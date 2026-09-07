from __future__ import annotations

from dataclasses import dataclass

from services.rotation_action_occupancy_legality_service import (
    RotationActionOccupancyAssessment,
    RotationActionOccupancyLegalityService,
    RotationActionOccupancyRule,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_resource_legality_service import (
    RotationCandidateResourceLegalityResult,
)


@dataclass(frozen=True)
class RotationCandidateActionOccupancyInput:
    """One resource-legal candidate plus explicit action timing evidence."""

    resource_result: RotationCandidateResourceLegalityResult
    occupancy_rules: tuple[RotationActionOccupancyRule, ...] = ()


@dataclass(frozen=True)
class RotationCandidateActionOccupancyResult:
    """Final candidate state after action occupancy legality."""

    resource_result: RotationCandidateResourceLegalityResult
    occupancy_assessment: RotationActionOccupancyAssessment
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return self.resource_result.candidate_id

    @property
    def generated_candidate(self):
        return self.resource_result.generated_candidate


class RotationCandidateActionOccupancyService:
    """Apply explicit action occupancy as another hard candidate gate.

    All upstream hard obligations remain authoritative. This layer only validates
    caller-supplied timing evidence. It does not invent cast times, channel times,
    GCDs, weave compatibility, or bar-swap lockouts.
    """

    def __init__(
        self,
        occupancy_service: RotationActionOccupancyLegalityService | None = None,
    ) -> None:
        self.occupancy_service = (
            occupancy_service or RotationActionOccupancyLegalityService()
        )

    def evaluate_and_rank(
        self,
        *,
        candidates: tuple[RotationCandidateActionOccupancyInput, ...],
    ) -> tuple[RotationCandidateActionOccupancyResult, ...]:
        if not candidates:
            return ()

        seen: set[str] = set()
        staged: list[
            tuple[tuple[object, ...], RotationCandidateActionOccupancyResult]
        ] = []

        for candidate in candidates:
            candidate_id = candidate.resource_result.candidate_id
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation occupancy candidate_id: {candidate_id!r}"
                )
            seen.add(key)

            plan = candidate.resource_result.generated_candidate.plan
            assessment = self.occupancy_service.assess(
                plan=plan,
                rules=tuple(candidate.occupancy_rules),
            )

            upstream_eligible = (
                candidate.resource_result.tier is RotationCandidateTier.ELIGIBLE
            )
            combined_eligible = upstream_eligible and assessment.is_legal
            reasons = (
                tuple(candidate.resource_result.reasons)
                + self._occupancy_reasons(assessment)
            )
            result = RotationCandidateActionOccupancyResult(
                resource_result=candidate.resource_result,
                occupancy_assessment=assessment,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if combined_eligible
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=0,
                reasons=reasons,
            )
            staged.append(
                (
                    (
                        0 if combined_eligible else 1,
                        len(assessment.unresolved),
                        len(assessment.violations),
                        0 if upstream_eligible else 1,
                        candidate.resource_result.rank,
                        candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationCandidateActionOccupancyResult(
                resource_result=result.resource_result,
                occupancy_assessment=result.occupancy_assessment,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )

    @staticmethod
    def _occupancy_reasons(
        assessment: RotationActionOccupancyAssessment,
    ) -> tuple[str, ...]:
        reasons = [
            f"rotation action occupancy violation at "
            f"{item.blocked_action.time_seconds:.3f}s: {item.reason} "
            f"(evidence: {item.source})"
            for item in assessment.violations
        ]
        reasons.extend(
            f"rotation action occupancy unresolved: {item}"
            for item in assessment.unresolved
        )
        return tuple(reasons)


__all__ = [
    "RotationCandidateActionOccupancyInput",
    "RotationCandidateActionOccupancyResult",
    "RotationCandidateActionOccupancyService",
]
