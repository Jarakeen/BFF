from __future__ import annotations

"""End-to-end Objective #32 proof wrapper over the global generated search tree."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceComposition,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)
from services.extreme_sustained_dps_generated_tree_coverage_service import (
    ExtremeSustainedDPSGeneratedTreeCoverageService,
)
from services.extreme_sustained_dps_objective32_blocker_service import (
    ExtremeSustainedDPSObjective32BlockerReport,
    ExtremeSustainedDPSObjective32BlockerService,
)
from services.extreme_sustained_dps_objective32_search_service import (
    ExtremeSustainedDPSObjective32SearchScopeProof,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosure,
    ExtremeSustainedDPSTheoreticalMaximumClosureService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGlobalObjective32SearchResult:
    search: object
    axis_inventory: object
    axis_coverage: ExtremeSustainedDPSAxisDominanceComposition
    closure: ExtremeSustainedDPSTheoreticalMaximumClosure
    scope_proof: ExtremeSustainedDPSObjective32SearchScopeProof | None
    blockers: ExtremeSustainedDPSObjective32BlockerReport
    supplemental_evidence: tuple[str, ...] = ()

    @property
    def best_modeled_dps(self) -> float | None:
        return getattr(self.search, "best_modeled_dps", None)

    @property
    def finite_denominator_maximum_proven(self) -> bool:
        return self.closure.finite_denominator_maximum_proven

    @property
    def theoretical_maximum_proven(self) -> bool:
        return self.closure.theoretical_maximum_proven


class ExtremeSustainedDPSGlobalObjective32SearchService:
    """Run the structural global tree and apply Objective #32 closure proof."""

    def __init__(
        self,
        *,
        global_search: object,
        structural_families: object | None = None,
    ) -> None:
        self.global_search = global_search
        self.structural_families = structural_families

    def search(
        self,
        *,
        coverage_proofs: tuple[ExtremeSustainedDPSAxisCoverageProof, ...] = (),
        scope_proof: ExtremeSustainedDPSObjective32SearchScopeProof | None = None,
        runtime_state_frontier=None,
        omitted_scope: tuple[str, ...] = (),
        root_key: str = "generated-global-root",
        **search_kwargs,
    ) -> ExtremeSustainedDPSGlobalObjective32SearchResult:
        normalized_root = str(root_key or "").strip() or "generated-global-root"

        axis_inventory = self.global_search.axis_inventory(
            runtime_state_frontier=runtime_state_frontier,
        )
        search = self.global_search.search(
            root_key=normalized_root,
            runtime_state_frontier=runtime_state_frontier,
            **search_kwargs,
        )

        tree_coverage = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
            search_result=search,
            axis_inventory=axis_inventory,
        )
        supplemental_proofs: tuple[ExtremeSustainedDPSAxisCoverageProof, ...] = ()
        supplemental_scope_note: tuple[str, ...] = ()
        if coverage_proofs:
            if scope_proof is None:
                supplemental_scope_note = (
                    "Supplemental Objective #32 coverage proofs were ignored because no denominator scope proof was supplied",
                )
            elif scope_proof.root_candidate_key != normalized_root:
                supplemental_scope_note = (
                    "Supplemental Objective #32 coverage proofs were ignored because their scope names a different generated search root",
                )
            elif not scope_proof.coverage_matches_search_denominator:
                supplemental_scope_note = (
                    "Supplemental Objective #32 coverage proofs were ignored because denominator equivalence is not proven",
                )
            else:
                supplemental_proofs = tuple(coverage_proofs)

        proofs = (
            tree_coverage.proof,
            *supplemental_proofs,
        )

        coverage = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
            normalized_root,
            required_axes=tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES),
            proofs=proofs,
        )
        inventory_unresolved: list[str] = []
        if axis_inventory.missing_canonical_axes:
            inventory_unresolved.append(
                "Generated global search tree does not physically enumerate canonical axis(es): "
                + ", ".join(axis_inventory.missing_canonical_axes)
            )
        inventory_unresolved.extend(tuple(axis_inventory.unresolved))

        closure = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            search,
            axis_coverage=coverage,
            omitted_scope=(
                *tuple(omitted_scope),
                *tuple(inventory_unresolved),
            ),
        )
        blockers = ExtremeSustainedDPSObjective32BlockerService.assess(
            search_result=search,
            axis_inventory=axis_inventory,
            axis_coverage=coverage,
            closure=closure,
        )

        return ExtremeSustainedDPSGlobalObjective32SearchResult(
            search=search,
            axis_inventory=axis_inventory,
            axis_coverage=coverage,
            closure=closure,
            scope_proof=scope_proof,
            blockers=blockers,
            supplemental_evidence=tuple(supplemental_scope_note),
        )


__all__ = [
    "ExtremeSustainedDPSGlobalObjective32SearchResult",
    "ExtremeSustainedDPSGlobalObjective32SearchService",
]
