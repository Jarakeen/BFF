from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_build import CharacterBuild
from services.rotation_build_timing_projection_service import (
    RotationBuildTimingPolicy,
    RotationBuildTimingProjection,
    RotationBuildTimingProjectionService,
)
from services.rotation_candidate_action_occupancy_service import (
    RotationCandidateActionOccupancyInput,
    RotationCandidateActionOccupancyResult,
    RotationCandidateActionOccupancyService,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_resource_legality_service import (
    RotationCandidateResourceLegalityResult,
)


@dataclass(frozen=True)
class RotationCandidateBuildTimingInput:
    """One resource-legal candidate evaluated against one build timing projection."""

    resource_result: RotationCandidateResourceLegalityResult


@dataclass(frozen=True)
class RotationCandidateBuildTimingResult:
    """Candidate state after automatic build-derived occupancy evaluation."""

    occupancy_result: RotationCandidateActionOccupancyResult
    timing_projection: RotationBuildTimingProjection
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return self.occupancy_result.candidate_id

    @property
    def generated_candidate(self):
        return self.occupancy_result.generated_candidate


class RotationCandidateBuildTimingService:
    """Apply canonical slotted-build timing to candidate occupancy automatically.

    This is the normal build-aware bridge between canonical cast/channel evidence and
    the existing occupancy hard gate. It does not invent global cooldowns, weave
    rules, bar-swap lockouts, passive timing modifiers, or missing skill timing.

    Any unresolved timing evidence for the build makes every candidate evaluated from
    that projection ineligible. Inventory coverage is not mechanic coverage: finding
    a slotted skill without enough canonical timing evidence never becomes zero-cost
    or zero-occupancy behavior by implication.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        projection_service: RotationBuildTimingProjectionService | None = None,
        occupancy_service: RotationCandidateActionOccupancyService | None = None,
    ) -> None:
        self.projection_service = projection_service or RotationBuildTimingProjectionService(
            database_path
        )
        self.occupancy_service = occupancy_service or RotationCandidateActionOccupancyService()

    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        policy: RotationBuildTimingPolicy,
        candidates: tuple[RotationCandidateBuildTimingInput, ...],
    ) -> tuple[RotationCandidateBuildTimingResult, ...]:
        if not candidates:
            return ()

        projection = self.projection_service.project(build=build, policy=policy)

        seen: set[str] = set()
        occupancy_inputs: list[RotationCandidateActionOccupancyInput] = []
        for candidate in candidates:
            candidate_id = candidate.resource_result.candidate_id
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation build-timing candidate_id: {candidate_id!r}"
                )
            seen.add(key)
            occupancy_inputs.append(
                RotationCandidateActionOccupancyInput(
                    resource_result=candidate.resource_result,
                    occupancy_rules=projection.rules,
                )
            )

        ranked = self.occupancy_service.evaluate_and_rank(candidates=tuple(occupancy_inputs))
        if {item.candidate_id.casefold() for item in ranked} != seen:
            raise ValueError("rotation occupancy ranking returned a different candidate set")

        staged: list[tuple[tuple[object, ...], RotationCandidateBuildTimingResult]] = []
        for item in ranked:
            projection_resolved = not projection.unresolved
            combined_eligible = (
                item.tier is RotationCandidateTier.ELIGIBLE and projection_resolved
            )
            reasons = tuple(item.reasons) + tuple(
                f"build timing projection unresolved: {detail}"
                for detail in projection.unresolved
            )
            result = RotationCandidateBuildTimingResult(
                occupancy_result=item,
                timing_projection=projection,
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
                        len(projection.unresolved),
                        0 if item.tier is RotationCandidateTier.ELIGIBLE else 1,
                        item.rank,
                        item.candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda entry: entry[0])
        return tuple(
            RotationCandidateBuildTimingResult(
                occupancy_result=result.occupancy_result,
                timing_projection=result.timing_projection,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )


__all__ = [
    "RotationCandidateBuildTimingInput",
    "RotationCandidateBuildTimingResult",
    "RotationCandidateBuildTimingService",
]
