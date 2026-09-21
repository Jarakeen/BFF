from __future__ import annotations

"""End-to-end proof wrapper for Extreme objective #32: MOST Sustained DPS."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceComposition,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosure,
    ExtremeSustainedDPSTheoreticalMaximumClosureService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32SearchResult:
    search: ExtremeSustainedDPSGeneratedSearchResult
    axis_coverage: ExtremeSustainedDPSAxisDominanceComposition
    closure: ExtremeSustainedDPSTheoreticalMaximumClosure

    @property
    def best_modeled_dps(self) -> float | None:
        return self.search.best_modeled_dps

    @property
    def finite_denominator_maximum_proven(self) -> bool:
        return self.closure.finite_denominator_maximum_proven

    @property
    def theoretical_maximum_proven(self) -> bool:
        return self.closure.theoretical_maximum_proven


class ExtremeSustainedDPSObjective32SearchService:
    """Run generated search and report finite-tree proof separately from theory."""

    def __init__(self, *, pipeline_search: object) -> None:
        self.pipeline_search = pipeline_search

    def search(
        self,
        root_state: object,
        *,
        coverage_proofs: tuple[ExtremeSustainedDPSAxisCoverageProof, ...],
        required_duration_seconds: float,
        runtime_snapshot: object,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
        root_key: str = "generated-root",
        root_bound_inputs=None,
        branch_bound_inputs=None,
        runtime_state_frontier=None,
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSObjective32SearchResult:
        search = self.pipeline_search.search(
            root_state,
            required_duration_seconds=float(required_duration_seconds),
            runtime_snapshot=runtime_snapshot,
            target_health=int(target_health),
            target_resistance=float(target_resistance),
            target_name=target_name,
            initial_bar=initial_bar,
            root_key=root_key,
            root_bound_inputs=root_bound_inputs,
            branch_bound_inputs=branch_bound_inputs,
            runtime_state_frontier=runtime_state_frontier,
        )

        proofs = tuple(coverage_proofs)
        if runtime_state_frontier is not None:
            proofs = (
                *proofs,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.coverage(
                    runtime_state_frontier
                ),
            )

        coverage = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
            "extreme-objective-32",
            required_axes=tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES),
            proofs=proofs,
        )
        closure = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            search,
            axis_coverage=coverage,
            omitted_scope=tuple(omitted_scope),
        )

        return ExtremeSustainedDPSObjective32SearchResult(
            search=search,
            axis_coverage=coverage,
            closure=closure,
        )


__all__ = [
    "ExtremeSustainedDPSObjective32SearchResult",
    "ExtremeSustainedDPSObjective32SearchService",
]
