from __future__ import annotations

"""Compose exact ordinary max-resource winners with every legal special-set subset.

This is the shared candidate-composition layer for max_health, max_magicka, and
max_stamina.  It reuses the already-proven subset search mechanics from the legacy
Max Health compositor while replacing the Health-only classifier with the canonical
objective-driven Max Resource classifier.

Max Magicka / Max Stamina additionally use semantic-prefix memoization for both the
ordinary branch and required-special subset search.  Max Health remains on the
legacy special-subset path until parity is reviewed separately.
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
from services.extreme_max_resource_semantic_memo_search_service import (
    ExtremeMaxResourceSemanticMemoSearchService,
)
from services.extreme_max_resource_semantic_special_subset_search_service import (
    ExtremeMaxResourceSemanticSpecialSubsetSearchService,
)
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchResult,
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_max_resource_special_subset_equivalence_service import (
    ExtremeMaxResourceSpecialSubsetEquivalenceService,
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
    _reuse_diagnostics: dict[str, int] = {}

    @classmethod
    def reuse_diagnostics(cls) -> dict[str, int]:
        return dict(cls._reuse_diagnostics)

    @classmethod
    def _reset_reuse_diagnostics(cls) -> None:
        cls._reuse_diagnostics = {
            "fitting_subsets_seen": 0,
            "structural_keys_built": 0,
            "representative_exact_searches": 0,
            "reuse_attempts": 0,
            "reuse_successes": 0,
            "rematerialization_failures": 0,
            "fallback_exact_searches": 0,
            "structural_classes_seen": 0,
        }

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
        if objective in {"max_magicka", "max_stamina"} and not isinstance(
            ordinary_service,
            ExtremeMaxResourceSemanticMemoSearchService,
        ):
            ordinary_service = ExtremeMaxResourceSemanticMemoSearchService(
                breakpoints=ordinary_service.breakpoints,
                eligibility=ordinary_service.eligibility,
                relevance=ordinary_service.relevance,
            )
        self.ordinary_service = ordinary_service
        self.eligibility = eligibility

    def _search_max_resource_subset(
        self,
        *,
        topology,
        subset,
        ordinary_candidates_by_count,
        frontier,
        feasibility,
    ) -> ExtremeMaxHealthSpecialSubsetWinner:
        if self.objective_key in {"max_magicka", "max_stamina"}:
            return ExtremeMaxResourceSemanticSpecialSubsetSearchService.search(
                self,
                topology=topology,
                subset=subset,
                ordinary_candidates_by_count=ordinary_candidates_by_count,
                frontier=frontier,
                feasibility=feasibility,
            )
        return self._search_subset(
            topology=topology,
            subset=subset,
            ordinary_candidates_by_count=ordinary_candidates_by_count,
            frontier=frontier,
            feasibility=feasibility,
        )

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeMaxResourceNamedGearCandidateSearchResult:
        type(self)._reset_reuse_diagnostics()
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
        eligibility_by_id = {int(row.set_id): row for row in self.eligibility.sets}
        reusable = self.objective_key in {"max_magicka", "max_stamina"}
        representative_cache: dict[
            tuple[object, ...],
            tuple[tuple[object, ...], ExtremeMaxHealthSpecialSubsetWinner],
        ] = {}

        for topology in topology_catalog.topologies:
            for size in range(1, len(branches) + 1):
                for subset in combinations(branches, size):
                    subset_tuple = tuple(subset)
                    if not self._subset_fits_counts(topology, subset_tuple):
                        continue
                    type(self)._reuse_diagnostics["fitting_subsets_seen"] += 1

                    structural_key = None
                    cached = None
                    if reusable:
                        structural_key = ExtremeMaxResourceSpecialSubsetEquivalenceService.structural_key(
                            topology=topology,
                            subset=subset_tuple,
                            ordinary_candidates_by_count=ordinary_candidates,
                            eligibility_by_id=eligibility_by_id,
                        )
                        if structural_key is not None:
                            type(self)._reuse_diagnostics["structural_keys_built"] += 1
                            cached = representative_cache.get(structural_key)
                            if cached is not None:
                                type(self)._reuse_diagnostics["reuse_attempts"] += 1
                                representative_subset, representative_winner = cached
                                rematerialized = ExtremeMaxResourceSpecialSubsetEquivalenceService.rematerialize(
                                    topology=topology,
                                    representative_subset=representative_subset,
                                    representative_winner=representative_winner,
                                    target_subset=subset_tuple,
                                    eligibility_by_id=eligibility_by_id,
                                )
                                if rematerialized is not None:
                                    type(self)._reuse_diagnostics["reuse_successes"] += 1
                                    subset_winners.append(rematerialized)
                                    continue
                                type(self)._reuse_diagnostics["rematerialization_failures"] += 1

                    winner = self._search_max_resource_subset(
                        topology=topology,
                        subset=subset_tuple,
                        ordinary_candidates_by_count=ordinary_candidates,
                        frontier=frontier,
                        feasibility=feasibility,
                    )
                    subset_winners.append(winner)
                    if reusable and structural_key is not None:
                        if cached is None:
                            type(self)._reuse_diagnostics["representative_exact_searches"] += 1
                            representative_cache[structural_key] = (subset_tuple, winner)
                            type(self)._reuse_diagnostics["structural_classes_seen"] += 1
                        else:
                            type(self)._reuse_diagnostics["fallback_exact_searches"] += 1

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
