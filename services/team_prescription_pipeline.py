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
from .team_prescription_candidate_source import (
    OpenSlotObjectiveEvaluator,
    OpenSlotProviderResolver,
    PrescribedCandidateSourceResult,
    PrescribedOpenSlotCandidate,
    evaluate_open_slot_candidate_source,
)
from .team_prescription_slot_constraints import PrescribedSlotBuildConstraint


@dataclass(frozen=True)
class TeamPrescriptionPipelineResult:
    candidate_pools: PrescribedCandidatePoolResult
    optimization: TeamPrescriptionOptimizationResult
    candidate_source: PrescribedCandidateSourceResult | None = None

    @property
    def final_roster(self) -> PrescribedRoster:
        return self.optimization.final_roster

    @property
    def unresolved(self) -> tuple[str, ...]:
        source_unresolved = (
            () if self.candidate_source is None else self.candidate_source.unresolved
        )
        return tuple(
            dict.fromkeys(
                (
                    *self.candidate_pools.unresolved,
                    *self.optimization.unresolved,
                    *source_unresolved,
                )
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


def run_automatic_team_prescription_candidate_pipeline(
    *,
    roster: PrescribedRoster,
    candidates: tuple[PrescribedOpenSlotCandidate, ...],
    evaluate_objective: OpenSlotObjectiveEvaluator,
    resolve_provider_requirements: OpenSlotProviderResolver | None = None,
    provider_requirements_by_slot: dict[str, tuple[str, ...]] | None = None,
    build_constraints_by_slot: dict[str, PrescribedSlotBuildConstraint] | None = None,
) -> TeamPrescriptionPipelineResult:
    """Generate honest open-slot evidence, then run the existing prescription path."""

    source = evaluate_open_slot_candidate_source(
        roster=roster,
        candidates=candidates,
        evaluate_objective=evaluate_objective,
        resolve_provider_requirements=resolve_provider_requirements,
        build_constraints_by_slot=build_constraints_by_slot,
    )
    inputs = tuple(
        PrescribedCandidatePoolInput(slot_name=slot_name, open_slot=evidence)
        for slot_name, rows in source.evidence_by_slot.items()
        for evidence in rows
    )
    result = run_team_prescription_candidate_pipeline(
        roster=roster,
        candidate_inputs=inputs,
        provider_requirements_by_slot=provider_requirements_by_slot,
    )
    return TeamPrescriptionPipelineResult(
        candidate_pools=result.candidate_pools,
        optimization=result.optimization,
        candidate_source=source,
    )
