from __future__ import annotations

"""Exact ordinary max-resource search with proof-safe semantic prefix memoization.

The underlying joint-feasibility search already proves topology legality before
score search. This layer removes repeated exact subtrees whose selected prefixes
are indistinguishable to every remaining decision:

* identical identity-free physical/effect semantics for the selected prefix;
* identical accumulated exact ordinary score;
* identical set identities that can still appear in a remaining position; and
* identical equal-count ordering boundary.

Used identities that cannot occur in any remaining candidate domain are irrelevant
to future distinct-ID legality. Collapsing only those states therefore preserves
all exact winners and semantic ties while avoiding repeated enumeration of concrete
named identities that have become observationally interchangeable.
"""

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_resource_joint_feasibility_search_service import (
    ExtremeMaxResourceJointFeasibilitySearchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeOrdinaryNamedGearTopologyWinner,
    _Candidate,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


class ExtremeMaxResourceSemanticMemoSearchService(
    ExtremeMaxResourceJointFeasibilitySearchService
):
    """Joint-feasibility search with exact semantic-prefix subtree memoization."""

    def _search_topology(
        self,
        topology: ExtremeGearSetCountTopology,
        candidates_by_count: dict[int, tuple[_Candidate, ...]],
        frontier: ExtremeGearSetBonusBreakpointCatalog,
        *,
        feasibility: ExtremePartialNamedGearPhysicalFeasibilityService,
    ) -> ExtremeOrdinaryNamedGearTopologyWinner:
        counts = tuple(int(value) for value in topology.counts)
        candidate_rows = tuple(candidates_by_count.get(count, ()) for count in counts)
        if any(not rows for rows in candidate_rows):
            return ExtremeOrdinaryNamedGearTopologyWinner(
                topology=topology,
                best_exact_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )
        if not self._identity_legality_possible(
            counts=counts,
            candidates_by_count=candidates_by_count,
        ):
            return ExtremeOrdinaryNamedGearTopologyWinner(
                topology=topology,
                best_exact_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )
        if not self._physical_shape_legality_possible(
            topology=topology,
            counts=counts,
            candidates_by_count=candidates_by_count,
            feasibility=feasibility,
        ):
            return ExtremeOrdinaryNamedGearTopologyWinner(
                topology=topology,
                best_exact_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )

        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=self.eligibility,
        )
        selected: list[_Candidate] = []
        used_ids: set[int] = set()
        best = float("-inf")
        winners_by_semantic_key: dict[
            tuple[tuple[object, ...], ...],
            ExtremeNamedGearSetRealization,
        ] = {}
        leaf_semantic_cache: dict[
            tuple[tuple[object, ...], ...],
            ExtremeNamedGearSetRealization | None,
        ] = {}

        # For each recursion depth retain only used identities that can still block a
        # remaining choice. An identity absent from every remaining domain cannot
        # affect any future distinct-ID decision and is safe to forget in memo state.
        future_ids: list[frozenset[int]] = [frozenset() for _ in range(len(counts) + 1)]
        running: set[int] = set()
        for position in range(len(counts) - 1, -1, -1):
            running.update(int(row.set_id) for row in candidate_rows[position])
            future_ids[position] = frozenset(running)

        visited_prefix_states: set[
            tuple[
                int,
                tuple[tuple[object, ...], ...],
                float,
                tuple[int, ...],
                int | None,
            ]
        ] = set()

        nodes = leaves = witness_checks = feasible_leaves = rejected_leaves = 0
        score_pruned = physical_pruned = 0
        semantic_duplicate_leaves = 0

        def semantic_key(
            rows: tuple[_Candidate, ...] | list[_Candidate],
        ) -> tuple[tuple[object, ...], ...]:
            return tuple(
                (
                    realizer._eligibility_shape_cached(row.eligibility),
                    row.objective_effect_signature,
                )
                for row in rows
            )

        def previous_equal_id(position: int) -> int | None:
            # At the terminal state there is no next topology position, so there is
            # no equal-count symmetry floor left to preserve in the memo key.
            if position >= len(counts):
                return None
            if position > 0 and counts[position - 1] == counts[position]:
                return int(selected[position - 1].set_id)
            return None

        def prefix_state(position: int, score: float):
            still_relevant_used = tuple(
                sorted(set(used_ids).intersection(future_ids[position]))
            )
            return (
                int(position),
                semantic_key(selected),
                float(score),
                still_relevant_used,
                previous_equal_id(position),
            )

        def seed_first_feasible(
            position: int,
            score: float,
        ) -> tuple[
            float,
            ExtremeNamedGearSetRealization,
            tuple[tuple[object, ...], ...],
        ] | None:
            if position >= len(counts):
                physical = tuple(row.eligibility for row in selected)
                witness = realizer._find_witness_cached(topology, physical)
                if witness is None:
                    return None
                return float(score), witness, semantic_key(selected)

            equal_floor = previous_equal_id(position)
            for row in candidate_rows[position]:
                if row.set_id in used_ids:
                    continue
                if equal_floor is not None and row.set_id <= equal_floor:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                physical_prefix = tuple(item.eligibility for item in selected)
                seeded = None
                if feasibility.is_possible(topology, physical_prefix):
                    seeded = seed_first_feasible(position + 1, score + row.exact_delta)
                used_ids.remove(row.set_id)
                selected.pop()
                if seeded is not None:
                    return seeded
            return None

        seeded = seed_first_feasible(0, 0.0)
        if seeded is not None:
            best, seeded_witness, seeded_key = seeded
            winners_by_semantic_key[seeded_key] = seeded_witness
        selected.clear()
        used_ids.clear()

        def visit(position: int, score: float) -> None:
            nonlocal best, nodes, leaves, witness_checks, feasible_leaves
            nonlocal rejected_leaves, score_pruned, physical_pruned
            nonlocal winners_by_semantic_key, semantic_duplicate_leaves

            state = prefix_state(position, score)
            if state in visited_prefix_states:
                return
            visited_prefix_states.add(state)
            nodes += 1

            remaining_bound = self._distinct_id_remaining_bound(
                counts=counts,
                position=position,
                candidates_by_count=candidates_by_count,
                used_ids=used_ids,
            )
            if remaining_bound is None:
                score_pruned += 1
                return
            if best != float("-inf") and score + remaining_bound < best - 1e-9:
                score_pruned += 1
                return

            if position >= len(counts):
                leaves += 1
                key = semantic_key(selected)
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

            equal_floor = previous_equal_id(position)
            for row in candidate_rows[position]:
                if row.set_id in used_ids:
                    continue
                if equal_floor is not None and row.set_id <= equal_floor:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                physical_prefix = tuple(item.eligibility for item in selected)
                if feasibility.is_possible(topology, physical_prefix):
                    visit(position + 1, score + row.exact_delta)
                else:
                    physical_pruned += 1
                used_ids.remove(row.set_id)
                selected.pop()

        visit(0, 0.0)
        winners = sorted(
            winners_by_semantic_key.values(),
            key=lambda witness: (
                witness.set_ids,
                witness.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in witness.assignments),
            ),
        )
        return ExtremeOrdinaryNamedGearTopologyWinner(
            topology=topology,
            best_exact_flat_delta=(None if best == float("-inf") else float(best)),
            realizations=tuple(winners),
            stats=self._stats(
                nodes=nodes,
                leaves=leaves,
                witness_checks=witness_checks,
                feasible_leaves=feasible_leaves,
                rejected_leaves=rejected_leaves,
                score_pruned=score_pruned,
                physical_pruned=physical_pruned,
                semantic_leaf_classes=len(leaf_semantic_cache),
                semantic_duplicate_leaves=semantic_duplicate_leaves,
            ),
        )


__all__ = ["ExtremeMaxResourceSemanticMemoSearchService"]
