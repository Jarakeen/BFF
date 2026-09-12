from __future__ import annotations

"""Compose exact ordinary max-resource winners with every legal special-set subset.

This is the shared candidate-composition layer for max_health, max_magicka, and
max_stamina.  It reuses the already-proven subset search mechanics from the legacy
Max Health compositor while replacing the Health-only classifier with the canonical
objective-driven Max Resource classifier.

The inheritance is intentionally compatibility-first: the Health implementation owns
no Health-specific search math inside ``_search_subset``; it only previously fixed the
objective at construction/classification time.  Keeping that proven search body in one
place avoids cloning several hundred lines while the callers migrate to the shared
contract.
"""

from dataclasses import dataclass
from itertools import combinations

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthNamedGearCandidateSearchService,
    ExtremeMaxHealthSpecialSubsetWinner,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchResult,
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


@dataclass(frozen=True)
class ExtremeMaxResourceNamedGearCandidateSearchResult:
    objective_key: str
    ordinary: ExtremeMaxResourceOrdinaryNamedGearSearchResult
    classified_special: ExtremeMaxResourceSpecialNamedGearBranchResult
    special_subsets: tuple[ExtremeMaxHealthSpecialSubsetWinner, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def candidate_reduction_proven(self) -> bool:
        return (
            self.ordinary.ordinary_denominator_proven
            and self.classified_special.denominator_classified
            and not self.unresolved
        )

    @staticmethod
    def _identity(row: ExtremeNamedGearSetRealization) -> tuple[object, ...]:
        return (
            tuple(row.set_ids),
            tuple(row.counts),
            row.weapon_shape.value,
            tuple((item.slot, item.set_id, item.weapon_type) for item in row.assignments),
        )

    @property
    def candidate_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        unique: dict[tuple[object, ...], ExtremeNamedGearSetRealization] = {}
        for row in self.ordinary.winning_realizations:
            unique.setdefault(self._identity(row), row)
        for subset in self.special_subsets:
            for row in subset.realizations:
                unique.setdefault(self._identity(row), row)
        return tuple(unique[key] for key in sorted(unique))


class ExtremeMaxResourceNamedGearCandidateSearchService(
    ExtremeMaxHealthNamedGearCandidateSearchService
):
    """Build the proof-safe named-gear candidate frontier for any Max Resource."""

    SUPPORTED_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})

    def __init__(
        self,
        *,
        ordinary_service: ExtremeMaxResourceOrdinaryNamedGearSearchService,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
    ) -> None:
        objective = str(ordinary_service.relevance.objective_key or "").strip().casefold()
        if objective not in self.SUPPORTED_OBJECTIVES:
            raise ValueError(
                f"Max Resource named-gear candidate composition does not support {objective!r}"
            )
        self.objective_key = objective
        self.ordinary_service = ordinary_service
        self.eligibility = eligibility

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeMaxResourceNamedGearCandidateSearchResult:
        ordinary = self.ordinary_service.search(topology_catalog)
        classified = ExtremeMaxResourceSpecialNamedGearBranchService(
            self.ordinary_service.relevance
        ).build(ordinary.special_or_nonflat_pairs)

        reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=self.ordinary_service.breakpoints,
            eligibility=self.eligibility,
            relevance=self.ordinary_service.relevance,
        )
        reduced, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
            topology_catalog
        )
        frontier, _frontier_pruned = self.ordinary_service._frontier(
            reduced,
            representative_limit,
        )
        ordinary_candidates, _special = self.ordinary_service._candidates(frontier)

        branches = tuple(classified.branches)
        subset_winners: list[ExtremeMaxHealthSpecialSubsetWinner] = []
        feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
        for topology in topology_catalog.topologies:
            for size in range(1, len(branches) + 1):
                for subset in combinations(branches, size):
                    subset_tuple = tuple(subset)
                    if not self._subset_fits_counts(topology, subset_tuple):
                        continue
                    subset_winners.append(
                        self._search_subset(
                            topology=topology,
                            subset=subset_tuple,
                            ordinary_candidates_by_count=ordinary_candidates,
                            frontier=frontier,
                            feasibility=feasibility,
                        )
                    )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *ordinary.unresolved,
                    *classified.unresolved,
                )
            )
        )
        return ExtremeMaxResourceNamedGearCandidateSearchResult(
            objective_key=self.objective_key,
            ordinary=ordinary,
            classified_special=classified,
            special_subsets=tuple(subset_winners),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeMaxResourceNamedGearCandidateSearchResult",
    "ExtremeMaxResourceNamedGearCandidateSearchService",
]
