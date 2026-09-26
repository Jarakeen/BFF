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
from services.extreme_sustained_dps_closure_inventory_service import (
    ExtremeSustainedDPSClosureInventoryService,
)
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosure,
    ExtremeSustainedDPSTheoreticalMaximumClosureService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32SearchScopeProof:
    root_candidate_key: str
    coverage_matches_search_denominator: bool
    source: str = "caller-supplied Objective #32 search-scope proof"

    def __post_init__(self) -> None:
        key = str(self.root_candidate_key or "").strip()
        source = str(self.source or "").strip()
        if not key:
            raise ValueError("Objective #32 search-scope proof requires root_candidate_key")
        if not source:
            raise ValueError("Objective #32 search-scope proof requires source")
        if not isinstance(self.coverage_matches_search_denominator, bool):
            raise TypeError(
                "Objective #32 search-scope coverage_matches_search_denominator must be boolean"
            )
        object.__setattr__(self, "root_candidate_key", key)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32SearchResult:
    search: ExtremeSustainedDPSGeneratedSearchResult
    axis_coverage: ExtremeSustainedDPSAxisDominanceComposition
    closure: ExtremeSustainedDPSTheoreticalMaximumClosure
    scope_proof: ExtremeSustainedDPSObjective32SearchScopeProof
    closure_inventory: object | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.search, ExtremeSustainedDPSGeneratedSearchResult):
            raise TypeError("Objective #32 search result requires canonical generated search result")
        if not isinstance(self.axis_coverage, ExtremeSustainedDPSAxisDominanceComposition):
            raise TypeError("Objective #32 search result requires canonical axis coverage composition")
        if not isinstance(self.closure, ExtremeSustainedDPSTheoreticalMaximumClosure):
            raise TypeError("Objective #32 search result requires canonical theoretical closure")
        if not isinstance(self.scope_proof, ExtremeSustainedDPSObjective32SearchScopeProof):
            raise TypeError("Objective #32 search result requires canonical scope proof")

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
        scope_proof: ExtremeSustainedDPSObjective32SearchScopeProof,
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
        closure_inventory: object | None = None,
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSObjective32SearchResult:
        if not isinstance(coverage_proofs, tuple):
            raise TypeError("Objective #32 coverage_proofs must be a tuple")
        if any(not isinstance(proof, ExtremeSustainedDPSAxisCoverageProof) for proof in coverage_proofs):
            raise TypeError("Objective #32 coverage_proofs must contain canonical axis coverage proofs")
        if not isinstance(scope_proof, ExtremeSustainedDPSObjective32SearchScopeProof):
            raise TypeError("Objective #32 search requires canonical scope proof")
        if not isinstance(omitted_scope, tuple):
            raise TypeError("Objective #32 omitted_scope must be a tuple")

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
            str(root_key or "").strip() or "generated-root",
            required_axes=tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES),
            proofs=proofs,
        )
        scope_unresolved: tuple[str, ...] = ()
        normalized_root = str(root_key or "").strip() or "generated-root"
        if scope_proof.root_candidate_key != normalized_root:
            scope_unresolved = (
                "Objective #32 coverage proof scope names a different generated search root",
            )
        elif not scope_proof.coverage_matches_search_denominator:
            scope_unresolved = (
                "Objective #32 axis coverage is not proven to match the generated search denominator",
            )

        effective_closure_inventory = (
            closure_inventory
            if closure_inventory is not None
            else ExtremeSustainedDPSClosureInventoryService.build()
        )
        closure = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            search,
            axis_coverage=coverage,
            omitted_scope=(
                *tuple(omitted_scope),
                *scope_unresolved,
            ),
            closure_inventory=effective_closure_inventory,
        )

        return ExtremeSustainedDPSObjective32SearchResult(
            search=search,
            axis_coverage=coverage,
            closure=closure,
            scope_proof=scope_proof,
            closure_inventory=effective_closure_inventory,
        )


__all__ = [
    "ExtremeSustainedDPSObjective32SearchScopeProof",
    "ExtremeSustainedDPSObjective32SearchResult",
    "ExtremeSustainedDPSObjective32SearchService",
]
