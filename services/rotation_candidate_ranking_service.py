from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import RotationResourceConsequenceKind


_RESOURCE_ORDER = {
    RotationResourceConsequenceKind.IMPROVED: 0,
    RotationResourceConsequenceKind.NEUTRAL: 1,
    RotationResourceConsequenceKind.MIXED: 2,
    RotationResourceConsequenceKind.WORSENED: 3,
}


class RotationCandidateTier(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True)
class RotationCandidateRankingInput:
    candidate_id: str
    scorecard: RotationCandidateScorecard

    def __post_init__(self) -> None:
        value = str(self.candidate_id or "").strip()
        if not value:
            raise ValueError("rotation ranking candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", value)


@dataclass(frozen=True)
class RotationCandidateRankingResult:
    candidate_id: str
    scorecard: RotationCandidateScorecard
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


class RotationCandidateRankingService:
    """Rank candidate rotations with hard obligations before soft consequences.

    This is intentionally lexicographic rather than weighted. A candidate that
    misses an explicit demand action, required static support effect, or incurs
    resource shortfall cannot outrank one that satisfies those supplied hard
    obligations merely because its Magicka numbers look prettier.

    Within the same eligibility tier, deterministic evidence ordering is used:
    fewer missing obligations, lower shortfall, fewer unresolved items, then
    resource consequence and resource deltas. The service does not invent role
    importance weights or claim that static support coverage proves runtime uptime.
    """

    def rank(
        self,
        candidates: tuple[RotationCandidateRankingInput, ...],
    ) -> tuple[RotationCandidateRankingResult, ...]:
        seen: set[str] = set()
        for item in candidates:
            key = item.candidate_id.casefold()
            if key in seen:
                raise ValueError(f"duplicate rotation ranking candidate_id: {item.candidate_id!r}")
            seen.add(key)

        ordered = sorted(candidates, key=self._sort_key)
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=item.candidate_id,
                scorecard=item.scorecard,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if item.scorecard.supplied_obligations_satisfied
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=index + 1,
                reasons=self._reasons(item.scorecard),
            )
            for index, item in enumerate(ordered)
        )

    @classmethod
    def _sort_key(cls, item: RotationCandidateRankingInput) -> tuple[object, ...]:
        scorecard = item.scorecard
        consequence = scorecard.consequence
        missing_demand = len(scorecard.missing_demand_requirements)
        missing_effects = len(scorecard.missing_required_effects)
        hard_failure_count = missing_demand + missing_effects + (1 if scorecard.candidate_shortfall > 0 else 0)

        return (
            0 if scorecard.supplied_obligations_satisfied else 1,
            hard_failure_count,
            missing_demand,
            missing_effects,
            int(scorecard.candidate_shortfall),
            len(scorecard.unresolved),
            _RESOURCE_ORDER[consequence.resource_kind],
            -int(consequence.minimum_resource_delta),
            -int(consequence.ending_resource_delta),
            int(consequence.total_cost_delta),
            int(consequence.wait_delta),
            item.candidate_id.casefold(),
        )

    @staticmethod
    def _reasons(scorecard: RotationCandidateScorecard) -> tuple[str, ...]:
        reasons: list[str] = []
        if scorecard.missing_demand_requirements:
            reasons.append(
                f"missing {len(scorecard.missing_demand_requirements)} explicit demand requirement(s)"
            )
        if scorecard.missing_required_effects:
            reasons.append(
                "missing static required effect(s): "
                + ", ".join(scorecard.missing_required_effects)
            )
        if scorecard.candidate_shortfall:
            reasons.append(f"resource shortfall {scorecard.candidate_shortfall}")
        if scorecard.unresolved:
            reasons.append(f"{len(scorecard.unresolved)} unresolved evidence item(s)")

        consequence = scorecard.consequence
        reasons.append(f"resource consequence {consequence.resource_kind.value}")
        reasons.append(
            "resource deltas: "
            f"minimum {consequence.minimum_resource_delta:+d}, "
            f"ending {consequence.ending_resource_delta:+d}, "
            f"cost {consequence.total_cost_delta:+d}, "
            f"waits {consequence.wait_delta:+d}"
        )
        return tuple(reasons)
