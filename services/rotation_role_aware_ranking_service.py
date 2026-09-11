from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessment,
    RotationGameplayPolicyStatus,
)


_DAMAGE_ROLES = {"damage", "damage_dealer", "dd", "dps"}
_SUPPORT_ROLES = {"healer", "tank", "support"}


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationRoleAwareRankingInput:
    """One whole-plan scorecard plus explicit role-policy measurements.

    The scorecard owns shared hard mechanics, effect, legality, sustain, and
    unresolved evidence. Role-specific encounter gates travel separately through
    ``role_hard_obligation_satisfied`` so they are never mislabeled as generic
    scorecard failures.

    Role evidence may be explicitly unknown. Missing evidence that is required for
    the selected role family makes the candidate ineligible rather than coercing an
    unknown measurement to zero. A role hard-obligation value of ``False`` fails the
    candidate; ``None`` fails closed because the hard-gate state is unresolved.

    ``gameplay_policy_assessment`` is contextual play-practice evidence, not mechanic
    truth. For Damage Dealer candidates, a resolved DISFAVORED assessment remains
    mechanically eligible but sorts behind otherwise valid practice-compliant or
    explicitly-overridden candidates. UNRESOLVED gameplay-policy evidence fails
    closed. Omitted assessment preserves legacy ranking behavior until the caller's
    evidence path is wired.
    """

    candidate_id: str
    scorecard: RotationCandidateScorecard
    role_key: str
    role_output_value: float | None
    role_output_label: str
    assigned_support_value: float | None
    assigned_support_label: str
    sustain_margin: float | None
    primary_role_displacement_seconds: float | None
    role_hard_obligation_satisfied: bool | None = True
    role_hard_obligation_reasons: tuple[str, ...] = ()
    gameplay_policy_assessment: RotationGameplayPolicyAssessment | None = None

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("role-aware rotation candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", candidate_id)

        role = _canonical(self.role_key)
        if role not in _DAMAGE_ROLES | _SUPPORT_ROLES:
            raise ValueError(f"unsupported role-aware rotation role: {self.role_key!r}")
        object.__setattr__(self, "role_key", role)

        assessment = self.gameplay_policy_assessment
        if assessment is not None and assessment.candidate_id.casefold() != candidate_id.casefold():
            raise ValueError(
                "gameplay-policy assessment candidate mismatch: "
                f"expected {candidate_id!r}, got {assessment.candidate_id!r}"
            )

        for field_name in (
            "role_output_value",
            "assigned_support_value",
            "sustain_margin",
            "primary_role_displacement_seconds",
        ):
            raw = getattr(self, field_name)
            if raw is None:
                continue
            value = float(raw)
            if not isfinite(value):
                raise ValueError(f"{field_name} must be finite when supplied")
            if field_name in {
                "assigned_support_value",
                "primary_role_displacement_seconds",
            } and value < 0.0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, value)

        for field_name in ("role_output_label", "assigned_support_label"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        object.__setattr__(
            self,
            "role_hard_obligation_reasons",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.role_hard_obligation_reasons
                    if str(item).strip()
                )
            ),
        )

    @property
    def role_family(self) -> str:
        return "damage" if self.role_key in _DAMAGE_ROLES else "support"

    @property
    def missing_required_role_evidence(self) -> tuple[str, ...]:
        required = (
            (
                ("role output", self.role_output_value),
                ("sustain margin", self.sustain_margin),
                ("primary-role displacement", self.primary_role_displacement_seconds),
            )
            if self.role_family == "damage"
            else (
                ("assigned support", self.assigned_support_value),
                ("sustain margin", self.sustain_margin),
                ("primary-role displacement", self.primary_role_displacement_seconds),
            )
        )
        return tuple(label for label, value in required if value is None)


@dataclass(frozen=True)
class RotationRoleAwareRankingResult:
    candidate_id: str
    tier: RotationCandidateTier
    rank: int
    base_ranking: RotationCandidateRankingResult
    role_reasons: tuple[str, ...]


class RotationRoleAwareRankingService:
    """Apply role policy only after shared and role-specific hard gates pass.

    The existing candidate ranker remains authoritative for mechanic correctness,
    required effects, runtime uptime floors, legality, resource reserves, sustain
    shortfall, and candidate-specific unresolved mechanics. This layer cannot rescue
    an ineligible plan. Explicit role hard obligations are an additional gate, not a
    weighted objective, and unresolved hard-gate evidence fails closed.

    Eligible Damage Dealer candidates prefer resolved gameplay-practice quality
    before effective role output when a gameplay assessment is supplied. A
    mechanically legal but unjustified redundant personal-heal candidate therefore
    remains eligible, yet cannot beat an otherwise valid practice-compliant or
    explicitly-overridden candidate merely by posting more damage. No weighted
    exchange rate is invented. Legacy candidates without a gameplay assessment keep
    the prior damage-first behavior until their evidence path is wired.

    Eligible healer/tank/support plans prioritize assigned support value, then
    sustain margin and primary-role displacement, before optional role output.
    Stable candidate identity is the final deterministic tie-break.
    """

    def __init__(
        self,
        base_ranking_service: RotationCandidateRankingService | None = None,
    ) -> None:
        self.base_ranking_service = base_ranking_service or RotationCandidateRankingService()

    def rank(
        self,
        candidates: tuple[RotationRoleAwareRankingInput, ...],
    ) -> tuple[RotationRoleAwareRankingResult, ...]:
        candidates = tuple(candidates)
        if not candidates:
            return ()
        self._validate_scope(candidates)

        base_results = self.base_ranking_service.rank(
            tuple(
                RotationCandidateRankingInput(item.candidate_id, item.scorecard)
                for item in candidates
            )
        )
        base_by_id = {item.candidate_id.casefold(): item for item in base_results}

        eligible = [
            item
            for item in candidates
            if self._is_role_eligible(item, base_by_id[item.candidate_id.casefold()])
        ]
        ineligible = [item for item in candidates if item not in eligible]
        eligible.sort(key=self._eligible_sort_key)
        ineligible.sort(
            key=lambda item: (
                base_by_id[item.candidate_id.casefold()].rank,
                self._hard_obligation_sort_key(item),
                self._gameplay_policy_sort_key(item),
                len(item.missing_required_role_evidence),
                item.candidate_id.casefold(),
                item.candidate_id,
            )
        )
        ordered = eligible + ineligible

        return tuple(
            RotationRoleAwareRankingResult(
                candidate_id=item.candidate_id,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if self._is_role_eligible(
                        item,
                        base_by_id[item.candidate_id.casefold()],
                    )
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=index + 1,
                base_ranking=base_by_id[item.candidate_id.casefold()],
                role_reasons=self._role_reasons(item),
            )
            for index, item in enumerate(ordered)
        )

    @staticmethod
    def _hard_obligation_sort_key(item: RotationRoleAwareRankingInput) -> int:
        if item.role_hard_obligation_satisfied is True:
            return 0
        if item.role_hard_obligation_satisfied is False:
            return 1
        return 2

    @staticmethod
    def _gameplay_policy_sort_key(item: RotationRoleAwareRankingInput) -> int:
        assessment = item.gameplay_policy_assessment
        if item.role_family != "damage" or assessment is None:
            return 0
        if assessment.status in {
            RotationGameplayPolicyStatus.SATISFIED,
            RotationGameplayPolicyStatus.OVERRIDDEN,
            RotationGameplayPolicyStatus.NOT_APPLICABLE,
        }:
            return 0
        if assessment.status is RotationGameplayPolicyStatus.DISFAVORED:
            return 1
        return 2

    @classmethod
    def _is_role_eligible(
        cls,
        item: RotationRoleAwareRankingInput,
        base: RotationCandidateRankingResult,
    ) -> bool:
        gameplay_policy_resolved = not (
            item.role_family == "damage"
            and item.gameplay_policy_assessment is not None
            and item.gameplay_policy_assessment.status
            is RotationGameplayPolicyStatus.UNRESOLVED
        )
        return (
            base.tier is RotationCandidateTier.ELIGIBLE
            and item.role_hard_obligation_satisfied is True
            and not item.missing_required_role_evidence
            and gameplay_policy_resolved
        )

    @staticmethod
    def _required(value: float | None, label: str) -> float:
        if value is None:
            raise ValueError(f"required role-aware ranking evidence missing: {label}")
        return value

    @classmethod
    def _eligible_sort_key(cls, item: RotationRoleAwareRankingInput) -> tuple[object, ...]:
        sustain = cls._required(item.sustain_margin, "sustain margin")
        displacement = cls._required(
            item.primary_role_displacement_seconds,
            "primary-role displacement",
        )
        if item.role_family == "damage":
            role_output = cls._required(item.role_output_value, "role output")
            return (
                cls._gameplay_policy_sort_key(item),
                -role_output,
                -sustain,
                displacement,
                item.candidate_id.casefold(),
                item.candidate_id,
            )
        assigned_support = cls._required(item.assigned_support_value, "assigned support")
        optional_output_missing = item.role_output_value is None
        optional_output = item.role_output_value if item.role_output_value is not None else 0.0
        return (
            -assigned_support,
            -sustain,
            displacement,
            optional_output_missing,
            -optional_output,
            item.candidate_id.casefold(),
            item.candidate_id,
        )

    @classmethod
    def _role_reasons(cls, item: RotationRoleAwareRankingInput) -> tuple[str, ...]:
        reasons: list[str] = []
        if item.role_hard_obligation_satisfied is False:
            reasons.append("role-specific hard obligation failed")
        elif item.role_hard_obligation_satisfied is None:
            reasons.append("role-specific hard obligation evidence unresolved")
        reasons.extend(item.role_hard_obligation_reasons)

        if item.missing_required_role_evidence:
            reasons.append(
                "role ranking evidence missing: "
                + ", ".join(item.missing_required_role_evidence)
            )

        assessment = item.gameplay_policy_assessment
        if item.role_family == "damage" and assessment is not None:
            reasons.append(
                "gameplay policy "
                f"{assessment.policy_id}: {assessment.status.value}"
            )
            reasons.extend(assessment.reasons)

        sustain = (
            f"{item.sustain_margin:g}"
            if item.sustain_margin is not None
            else "unknown"
        )
        displacement = (
            f"{item.primary_role_displacement_seconds:g}s"
            if item.primary_role_displacement_seconds is not None
            else "unknown"
        )
        if item.role_family == "damage":
            role_output = (
                f"{item.role_output_value:g}"
                if item.role_output_value is not None
                else "unknown"
            )
            support = (
                f"{item.assigned_support_value:g}"
                if item.assigned_support_value is not None
                else "not supplied"
            )
            reasons.extend(
                (
                    f"DD policy: {item.role_output_label}={role_output} is the first soft objective after hard validity and gameplay-practice quality.",
                    f"Sustain margin={sustain}; primary-role displacement={displacement}.",
                    f"{item.assigned_support_label}={support} is diagnostic unless the scorecard makes it a hard assigned obligation.",
                )
            )
            return tuple(reasons)

        assigned_support = (
            f"{item.assigned_support_value:g}"
            if item.assigned_support_value is not None
            else "unknown"
        )
        role_output = (
            f"{item.role_output_value:g}"
            if item.role_output_value is not None
            else "not supplied"
        )
        reasons.extend(
            (
                f"Support policy: {item.assigned_support_label}={assigned_support} is the first soft objective after hard validity.",
                f"Sustain margin={sustain}; primary-role displacement={displacement}.",
                f"Optional {item.role_output_label}={role_output} is considered only after support practicality remains valid.",
            )
        )
        return tuple(reasons)

    @staticmethod
    def _validate_scope(candidates: tuple[RotationRoleAwareRankingInput, ...]) -> None:
        role = candidates[0].role_key
        output_label = candidates[0].role_output_label.casefold()
        support_label = candidates[0].assigned_support_label.casefold()
        seen: set[str] = set()
        for item in candidates:
            if item.role_key != role:
                raise ValueError("role-aware rotation ranking requires one shared role")
            if item.role_output_label.casefold() != output_label:
                raise ValueError("role-aware rotation ranking requires one shared role-output metric")
            if item.assigned_support_label.casefold() != support_label:
                raise ValueError("role-aware rotation ranking requires one shared support metric")
            key = item.candidate_id.casefold()
            if key in seen:
                raise ValueError(f"duplicate role-aware rotation candidate_id: {item.candidate_id!r}")
            seen.add(key)


__all__ = [
    "RotationRoleAwareRankingInput",
    "RotationRoleAwareRankingResult",
    "RotationRoleAwareRankingService",
]
