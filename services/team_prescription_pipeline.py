from __future__ import annotations

from dataclasses import dataclass

from .team_prescription import PrescribedRoster
from .team_prescription_candidate_pool import (
    PrescribedCandidatePoolInput,
    PrescribedCandidatePoolResult,
    build_prescribed_candidate_pools,
)
from .team_prescription_optimizer import (
    TeamPrescriptionOptimizationResult,
    optimize_prescribed_roster_candidates,
)


@dataclass(frozen=True)
class TeamPrescriptionPipelineResult:
    candidate_pools: PrescribedCandidatePoolResult
    optimization: TeamPrescriptionOptimizationResult

    @property
    def final_roster(self) -> PrescribedRoster:
        return self.optimization.final_roster

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (*self.candidate_pools.unresolved, *self.optimization.unresolved)
            )
        )


def run_team_prescription_candidate_pipeline(
    *,
    roster: PrescribedRoster,
    candidate_inputs: tuple[PrescribedCandidatePoolInput, ...],
    provider_requirements_by_slot: dict[str, tuple[str, ...]] | None = None,
) -> TeamPrescriptionPipelineResult:
    """Run the evidence-backed candidate portion of roster prescription end to end.

    Candidate generation/evaluation remains outside this function. The pipeline accepts
    only Phase 12 comparisons that already exist, groups them by open slot, applies the
    roster role/provider gates, ranks the survivors, and writes unique winners into a
    new non-destructive PrescribedRoster.
    """

    pools = build_prescribed_candidate_pools(
        roster=roster,
        inputs=candidate_inputs,
    )
    optimization = optimize_prescribed_roster_candidates(
        roster=roster,
        candidate_pools=pools.pools,
        provider_requirements_by_slot=provider_requirements_by_slot,
    )
    return TeamPrescriptionPipelineResult(
        candidate_pools=pools,
        optimization=optimization,
    )
