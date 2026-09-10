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


_DAMAGE_ROLES = {"damage", "damage_dealer", "dd", "dps"}
_SUPPORT_ROLES = {"healer", "tank", "support"}


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationRoleAwareRankingInput:
    """One whole-plan scorecard plus explicit role-policy measurements.

    The scorecard owns hard mechanics, effect, legality, sustain, and unresolved
    evidence. These values are downstream measurements only; this policy layer does
    not recompute ESO truth or convert unlike dimensions into a weighted score.

    Role evidence may be explicitly unknown. Missing evidence that is required for
    the selected role family makes the candidate ineligible rather than coercing an
    unknown measurement to zero. Damage Dealer ranking requires role output,
    sustain margin, and primary-role displacement. Support ranking requires assigned
    support, sustain margin, and primary-role displacement. Incidental support on a
    DD and optional output on a support plan remain diagnostic/soft evidence.
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

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("role-aware rotation candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", candidate_id)

        role = _canonical(self.role_key)
        if role not in _DAMAGE_ROLES | _SUPPORT_ROLES:
            raise ValueError(f"unsupported role-aware rotation role: {self.role_key!r}")
        object.__setattr__(self, "role_key", role)

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
    """Apply role policy only after shared whole-plan hard gates pass.

    The existing candidate ranker remains authoritative for mechanic correctness,
    required effects, runtime uptime floors, legality, resource reserves, sustain
    shortfall, and candidate-specific unresolved mechanics. This layer cannot rescue
    an ineligible plan. It also fails closed when role-critical comparison evidence
    is absent instead of treating missing measurements as numeric zeroes.

    Eligible Damage Dealer candidates prioritize effective role output first. Extra
    support value does not make a DD plan win unless that support was already an
    explicit hard obligation in the scorecard. Eligible healer/tank/support plans
    prioritize assigned support value, then sustain margin and primary-role
    displacement, before optional role output. Stable candidate identity is the
    final deterministic tie-break. No weighted exchange rate is invented.
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
    def _is_role_eligible(
        item: RotationRoleAwareRankingInput,
        base: RotationCandidateRankingResult,
    ) -> bool:
        return (
            base.tier is RotationCandidateTier.ELIGIBLE
            and not item.missing_required_role_evidence
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
        if item.missing_required_role_evidence:
            reasons.append(
                "role ranking evidence missing: "
                + ", ".join(item.missing_required_role_evidence)
            )

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
                    f"DD policy: {item.role_output_label}={role_output} is the first soft objective after hard validity.",
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
