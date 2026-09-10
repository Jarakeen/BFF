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
_EPSILON = 1e-9


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationRoleAwareRankingInput:
    """One whole-plan scorecard plus explicit role-policy measurements.

    The scorecard owns hard mechanics, effect, legality, sustain, and unresolved
    evidence. These values are downstream measurements only; this policy layer does
    not recompute ESO truth or convert unlike dimensions into a weighted score.
    """

    candidate_id: str
    scorecard: RotationCandidateScorecard
    role_key: str
    role_output_value: float
    role_output_label: str
    assigned_support_value: float
    assigned_support_label: str
    sustain_margin: float
    primary_role_displacement_seconds: float

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
            value = float(getattr(self, field_name))
            if not isfinite(value):
                raise ValueError(f"{field_name} must be finite")
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


@dataclass(frozen=True)
class RotationRoleAwareRankingResult:
    candidate_id: str
    tier: RotationCandidateTier
    rank: int
    base_ranking: RotationCandidateRankingResult
    role_reasons: tuple[str, ...]


class RotationRoleAwareRankingService:
    """Apply role policy only after the shared whole-plan hard gates pass.

    The existing candidate ranker remains authoritative for mechanic correctness,
    required effects, runtime uptime floors, legality, resource reserves, sustain
    shortfall, and candidate-specific unresolved evidence. This layer cannot rescue
    an ineligible plan.

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
            if base_by_id[item.candidate_id.casefold()].tier is RotationCandidateTier.ELIGIBLE
        ]
        ineligible = [
            item
            for item in candidates
            if base_by_id[item.candidate_id.casefold()].tier is RotationCandidateTier.INELIGIBLE
        ]
        eligible.sort(key=self._eligible_sort_key)
        ineligible.sort(key=lambda item: base_by_id[item.candidate_id.casefold()].rank)
        ordered = eligible + ineligible

        return tuple(
            RotationRoleAwareRankingResult(
                candidate_id=item.candidate_id,
                tier=base_by_id[item.candidate_id.casefold()].tier,
                rank=index + 1,
                base_ranking=base_by_id[item.candidate_id.casefold()],
                role_reasons=self._role_reasons(item),
            )
            for index, item in enumerate(ordered)
        )

    @classmethod
    def _eligible_sort_key(cls, item: RotationRoleAwareRankingInput) -> tuple[object, ...]:
        if item.role_family == "damage":
            return (
                -item.role_output_value,
                -item.sustain_margin,
                item.primary_role_displacement_seconds,
                item.candidate_id.casefold(),
                item.candidate_id,
            )
        return (
            -item.assigned_support_value,
            -item.sustain_margin,
            item.primary_role_displacement_seconds,
            -item.role_output_value,
            item.candidate_id.casefold(),
            item.candidate_id,
        )

    @classmethod
    def _role_reasons(cls, item: RotationRoleAwareRankingInput) -> tuple[str, ...]:
        if item.role_family == "damage":
            return (
                f"DD policy: {item.role_output_label}={item.role_output_value:g} is the first soft objective after hard validity.",
                f"Sustain margin={item.sustain_margin:g}; primary-role displacement={item.primary_role_displacement_seconds:g}s.",
                f"{item.assigned_support_label}={item.assigned_support_value:g} is diagnostic unless the scorecard makes it a hard assigned obligation.",
            )
        return (
            f"Support policy: {item.assigned_support_label}={item.assigned_support_value:g} is the first soft objective after hard validity.",
            f"Sustain margin={item.sustain_margin:g}; primary-role displacement={item.primary_role_displacement_seconds:g}s.",
            f"Optional {item.role_output_label}={item.role_output_value:g} is considered only after support practicality remains valid.",
        )

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
