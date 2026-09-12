from __future__ import annotations

"""Compose exact ordinary Max Health winners with every legal special-set subset.

The ordinary max-resource branch-and-bound service proves the best exact flat
named-gear continuation when no conditional/search-state breakpoint is selected.
For Max Health, excluded special breakpoints can still win after canonical runtime,
percentage, food, transformation, stack, or Mundus evaluation.

This service therefore enumerates every non-empty subset of the classified special
breakpoints that can fit a topology, fixes those identities into the branch, and
branch-and-bounds only the remaining ordinary exact-flat fillers. Special effects
contribute zero to the pruning score, so the bound is deliberately optimistic and
cannot discard a stronger special branch. Ordinary filler leaves are collapsed only
when their full requested-objective effect signatures and physical eligibility are
identical; special identities remain explicit in every semantic key.
"""

from dataclasses import dataclass
from itertools import combinations

from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialNamedGearBranch,
    ExtremeMaxHealthSpecialNamedGearBranchResult,
    ExtremeMaxHealthSpecialNamedGearBranchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialSubsetSearchStats:
    nodes: int = 0
    leaves: int = 0
    witness_checks: int = 0
    feasible_leaves: int = 0
    rejected_leaves: int = 0
    score_pruned: int = 0
    physical_pruned: int = 0
    requirement_pruned: int = 0
    semantic_leaf_classes: int = 0
    semantic_duplicate_leaves: int = 0


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialSubsetWinner:
    topology: ExtremeGearSetCountTopology
    special_pairs: tuple[tuple[int, str, int], ...]
    best_ordinary_flat_delta: float | None
    realizations: tuple[ExtremeNamedGearSetRealization, ...]
    stats: ExtremeMaxHealthSpecialSubsetSearchStats

    @property
    def winner_found(self) -> bool:
        return self.best_ordinary_flat_delta is not None and bool(self.realizations)


@dataclass(frozen=True)
class ExtremeMaxHealthNamedGearCandidateSearchResult:
    ordinary: ExtremeMaxResourceOrdinaryNamedGearSearchResult
    classified_special: ExtremeMaxHealthSpecialNamedGearBranchResult
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


@dataclass(frozen=True)
class _SearchCandidate:
    set_id: int
    name: str
    piece_count: int
    exact_delta: float
    eligibility: ExtremeNamedGearSetSlotEligibility
    objective_effect_signature: tuple[tuple[object, ...], ...] = ()
    special: bool = False


class ExtremeMaxHealthNamedGearCandidateSearchService:
    """Build the proof-safe reduced named-gear candidate frontier for Max Health."""

    def __init__(
        self,
        *,
        ordinary_service: ExtremeMaxResourceOrdinaryNamedGearSearchService,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
    ) -> None:
        objective = str(ordinary_service.relevance.objective_key or "").strip().casefold()
        if objective != "max_health":
            raise ValueError("Max Health named-gear candidate composition supports max_health only")
        self.ordinary_service = ordinary_service
        self.eligibility = eligibility

    @staticmethod
    def _pair(branch: ExtremeMaxHealthSpecialNamedGearBranch) -> tuple[int, str, int]:
        return (int(branch.set_id), str(branch.set_name), int(branch.piece_count))

    @staticmethod
    def _subset_fits_counts(
        topology: ExtremeGearSetCountTopology,
        subset: tuple[ExtremeMaxHealthSpecialNamedGearBranch, ...],
    ) -> bool:
        available: dict[int, int] = {}
        for count in topology.counts:
            available[int(count)] = available.get(int(count), 0) + 1
        required: dict[int, int] = {}
        for branch in subset:
            required[int(branch.piece_count)] = required.get(int(branch.piece_count), 0) + 1
        return all(required_count <= available.get(count, 0) for count, required_count in required.items())

    @staticmethod
    def _stats(**values: int) -> ExtremeMaxHealthSpecialSubsetSearchStats:
        return ExtremeMaxHealthSpecialSubsetSearchStats(**values)

    def _search_subset(
        self,
        *,
        topology: ExtremeGearSetCountTopology,
        subset: tuple[ExtremeMaxHealthSpecialNamedGearBranch, ...],
        ordinary_candidates_by_count,
        frontier,
        feasibility: ExtremePartialNamedGearPhysicalFeasibilityService,
    ) -> ExtremeMaxHealthSpecialSubsetWinner:
        counts = tuple(int(value) for value in topology.counts)
        eligibility_by_id = {int(row.set_id): row for row in self.eligibility.sets}
        special_by_count: dict[int, tuple[_SearchCandidate, ...]] = {}
        special_ids: set[int] = set()
        unresolved_special: list[tuple[int, str, int]] = []

        for branch in subset:
            physical = eligibility_by_id.get(int(branch.set_id))
            if physical is None or not physical.has_physical_slot_evidence:
                unresolved_special.append(self._pair(branch))
                continue
            candidate = _SearchCandidate(
                set_id=int(branch.set_id),
                name=str(branch.set_name),
                piece_count=int(branch.piece_count),
                exact_delta=0.0,
                eligibility=physical,
                objective_effect_signature=(),
                special=True,
            )
            special_by_count.setdefault(int(branch.piece_count), ())
            special_by_count[int(branch.piece_count)] = (
                *special_by_count[int(branch.piece_count)], candidate
            )
            special_ids.add(int(branch.set_id))

        pairs = tuple(sorted((self._pair(row) for row in subset), key=lambda row: (row[2], row[0], row[1].casefold())))
        if unresolved_special:
            return ExtremeMaxHealthSpecialSubsetWinner(
                topology=topology,
                special_pairs=pairs,
                best_ordinary_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )

        combined_by_count: dict[int, tuple[_SearchCandidate, ...]] = {}
        for count in set(counts):
            ordinary_rows = tuple(
                _SearchCandidate(
                    set_id=int(row.set_id),
                    name=str(row.name),
                    piece_count=int(row.piece_count),
                    exact_delta=float(row.exact_delta),
                    eligibility=row.eligibility,
                    objective_effect_signature=tuple(row.objective_effect_signature),
                    special=False,
                )
                for row in ordinary_candidates_by_count.get(int(count), ())
                if int(row.set_id) not in special_ids
            )
            special_rows = tuple(special_by_count.get(int(count), ()))
            combined_by_count[int(count)] = tuple(
                sorted(
                    (*ordinary_rows, *special_rows),
                    key=lambda row: (-row.exact_delta, row.set_id, row.name.casefold(), row.name),
                )
            )

        rows_by_position = tuple(combined_by_count.get(int(count), ()) for count in counts)
        if any(not rows for rows in rows_by_position):
            return ExtremeMaxHealthSpecialSubsetWinner(
                topology=topology,
                special_pairs=pairs,
                best_ordinary_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )

        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=self.eligibility,
        )
        selected: list[_SearchCandidate] = []
        used_ids: set[int] = set()
        selected_special_ids: set[int] = set()
        best = float("-inf")
        winners_by_semantic_key: dict[
            tuple[tuple[object, ...], ...],
            ExtremeNamedGearSetRealization,
        ] = {}
        leaf_semantic_cache: dict[
            tuple[tuple[object, ...], ...],
            ExtremeNamedGearSetRealization | None,
        ] = {}
        nodes = leaves = witness_checks = feasible_leaves = rejected_leaves = 0
        score_pruned = physical_pruned = requirement_pruned = 0
        semantic_duplicate_leaves = 0

        def remaining_positions_for_count(position: int, count: int) -> int:
            return sum(1 for value in counts[position:] if int(value) == int(count))

        def semantic_key() -> tuple[tuple[object, ...], ...]:
            rows: list[tuple[object, ...]] = []
            for row in selected:
                physical_shape = realizer._eligibility_shape_cached(row.eligibility)
                if row.special:
                    rows.append(
                        (
                            "special",
                            int(row.set_id),
                            int(row.piece_count),
                            physical_shape,
                        )
                    )
                else:
                    rows.append(
                        (
                            "ordinary",
                            physical_shape,
                            row.objective_effect_signature,
                        )
                    )
            return tuple(rows)

        def visit(position: int, score: float) -> None:
            nonlocal best, winners_by_semantic_key
            nonlocal nodes, leaves, witness_checks, feasible_leaves, rejected_leaves
            nonlocal score_pruned, physical_pruned, requirement_pruned
            nonlocal semantic_duplicate_leaves
            nodes += 1

            remaining_bound = self.ordinary_service._distinct_id_remaining_bound(
                counts=counts,
                position=position,
                candidates_by_count=combined_by_count,
                used_ids=used_ids,
            )
            if remaining_bound is None:
                score_pruned += 1
                return
            if best != float("-inf") and score + remaining_bound < best - 1e-9:
                score_pruned += 1
                return

            if position >= len(counts):
                if selected_special_ids != special_ids:
                    requirement_pruned += 1
                    return
                leaves += 1
                key = semantic_key()
                if key in leaf_semantic_cache:
                    semantic_duplicate_leaves += 1
                    witness = leaf_semantic_cache[key]
                else:
                    physical = tuple(row.eligibility for row in selected)
                    witness_checks += 1
                    witness = realizer._find_witness_cached(topology, physical)
                    leaf_semantic_cache[key] = witness
                if witness is None:
                    rejected_leaves += 1
                    return
                feasible_leaves += 1
                if score > best + 1e-9:
                    best = score
                    winners_by_semantic_key = {key: witness}
                elif abs(score - best) <= 1e-9:
                    winners_by_semantic_key.setdefault(key, witness)
                return

            count = int(counts[position])
            remaining_required = {
                row.set_id
                for row in special_by_count.get(count, ())
                if row.set_id not in selected_special_ids
            }
            remaining_slots = remaining_positions_for_count(position, count)
            if len(remaining_required) > remaining_slots:
                requirement_pruned += 1
                return

            previous_equal_id: int | None = None
            if position > 0 and counts[position - 1] == counts[position]:
                previous_equal_id = selected[position - 1].set_id

            for row in rows_by_position[position]:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                if len(remaining_required) == remaining_slots and row.set_id not in remaining_required:
                    continue

                selected.append(row)
                used_ids.add(row.set_id)
                if row.special:
                    selected_special_ids.add(row.set_id)
                prefix = tuple(item.eligibility for item in selected)
                if feasibility.is_possible(topology, prefix):
                    visit(position + 1, score + row.exact_delta)
                else:
                    physical_pruned += 1
                if row.special:
                    selected_special_ids.remove(row.set_id)
                used_ids.remove(row.set_id)
                selected.pop()

        visit(0, 0.0)
        winners = sorted(
            winners_by_semantic_key.values(),
            key=lambda witness: (
                witness.set_ids,
                witness.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in witness.assignments),
            )
        )
        return ExtremeMaxHealthSpecialSubsetWinner(
            topology=topology,
            special_pairs=pairs,
            best_ordinary_flat_delta=(None if best == float("-inf") else float(best)),
            realizations=tuple(winners),
            stats=self._stats(
                nodes=nodes,
                leaves=leaves,
                witness_checks=witness_checks,
                feasible_leaves=feasible_leaves,
                rejected_leaves=rejected_leaves,
                score_pruned=score_pruned,
                physical_pruned=physical_pruned,
                requirement_pruned=requirement_pruned,
                semantic_leaf_classes=len(leaf_semantic_cache),
                semantic_duplicate_leaves=semantic_duplicate_leaves,
            ),
        )

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeMaxHealthNamedGearCandidateSearchResult:
        ordinary = self.ordinary_service.search(topology_catalog)
        classified = ExtremeMaxHealthSpecialNamedGearBranchService(
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
        return ExtremeMaxHealthNamedGearCandidateSearchResult(
            ordinary=ordinary,
            classified_special=classified,
            special_subsets=tuple(subset_winners),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeMaxHealthNamedGearCandidateSearchResult",
    "ExtremeMaxHealthNamedGearCandidateSearchService",
    "ExtremeMaxHealthSpecialSubsetSearchStats",
    "ExtremeMaxHealthSpecialSubsetWinner",
]
