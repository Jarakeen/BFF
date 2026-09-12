from __future__ import annotations

"""Proof-safe semantic memo search for Max Resource special named-gear subsets.

The legacy Max Health special-subset search uses an unbounded recursive seed before
its exact DFS.  For Max Magicka / Max Stamina that seed can traverse millions of
ordinary filler identities before finding one required-special completion.  This
service removes the seed entirely and performs one exact branch-and-bound search
with the same semantic-prefix memo contract already proven for the ordinary Max
Resource branch.

Special identities remain explicit in every semantic state.  Ordinary identities
are forgotten only when they cannot appear in any remaining candidate domain.
Therefore memoized states have identical future legal continuations, while search
still enumerates every distinct semantic special branch required by the denominator.
"""

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthSpecialSubsetWinner,
    _SearchCandidate,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


class ExtremeMaxResourceSemanticSpecialSubsetSearchService:
    """Execute one fixed special subset with exact semantic-prefix memoization."""

    @staticmethod
    def search(
        owner,
        *,
        topology: ExtremeGearSetCountTopology,
        subset,
        ordinary_candidates_by_count,
        frontier,
        feasibility: ExtremePartialNamedGearPhysicalFeasibilityService,
    ) -> ExtremeMaxHealthSpecialSubsetWinner:
        counts = tuple(int(value) for value in topology.counts)
        eligibility_by_id = {int(row.set_id): row for row in owner.eligibility.sets}
        special_by_count: dict[int, tuple[_SearchCandidate, ...]] = {}
        special_ids: set[int] = set()
        unresolved_special: list[tuple[int, str, int]] = []

        for branch in subset:
            physical = eligibility_by_id.get(int(branch.set_id))
            if physical is None or not physical.has_physical_slot_evidence:
                unresolved_special.append(
                    (int(branch.set_id), str(branch.set_name), int(branch.piece_count))
                )
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
            count = int(branch.piece_count)
            special_by_count[count] = (*special_by_count.get(count, ()), candidate)
            special_ids.add(int(branch.set_id))

        pairs = tuple(
            sorted(
                (
                    (int(row.set_id), str(row.set_name), int(row.piece_count))
                    for row in subset
                ),
                key=lambda row: (row[2], row[0], row[1].casefold()),
            )
        )
        if unresolved_special:
            return ExtremeMaxHealthSpecialSubsetWinner(
                topology=topology,
                special_pairs=pairs,
                best_ordinary_flat_delta=None,
                realizations=(),
                stats=owner._stats(),
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
                    key=lambda row: (
                        -row.exact_delta,
                        row.set_id,
                        row.name.casefold(),
                        row.name,
                    ),
                )
            )

        rows_by_position = tuple(combined_by_count.get(int(count), ()) for count in counts)
        if any(not rows for rows in rows_by_position):
            return ExtremeMaxHealthSpecialSubsetWinner(
                topology=topology,
                special_pairs=pairs,
                best_ordinary_flat_delta=None,
                realizations=(),
                stats=owner._stats(),
            )

        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=owner.eligibility,
        )

        # Candidate semantic atoms are immutable. Build each once, then push/pop the
        # atom alongside the selected candidate instead of reconstructing every
        # selected prefix on every DFS node.
        semantic_atom_by_object_id: dict[int, tuple[object, ...]] = {}
        for rows in rows_by_position:
            for row in rows:
                object_id = id(row)
                if object_id in semantic_atom_by_object_id:
                    continue
                physical_shape = realizer._eligibility_shape_cached(row.eligibility)
                if row.special:
                    semantic_atom_by_object_id[object_id] = (
                        "special",
                        int(row.set_id),
                        int(row.piece_count),
                        physical_shape,
                    )
                else:
                    semantic_atom_by_object_id[object_id] = (
                        "ordinary",
                        physical_shape,
                        row.objective_effect_signature,
                    )

        selected: list[_SearchCandidate] = []
        selected_semantics: list[tuple[object, ...]] = []
        selected_eligibilities = []
        used_ids: set[int] = set()
        selected_special_ids: set[int] = set()
        best = float("-inf")
        winners_by_semantic_key: dict[
            tuple[tuple[object, ...], ...], ExtremeNamedGearSetRealization
        ] = {}
        leaf_semantic_cache: dict[
            tuple[tuple[object, ...], ...], ExtremeNamedGearSetRealization | None
        ] = {}

        future_ids: list[frozenset[int]] = [frozenset() for _ in range(len(counts) + 1)]
        running: set[int] = set()
        for position in range(len(counts) - 1, -1, -1):
            running.update(int(row.set_id) for row in rows_by_position[position])
            future_ids[position] = frozenset(running)

        # Both of these are pure functions of topology position. Precompute once
        # rather than rebuilding count histograms/scanning suffixes on every node.
        remaining_slots_by_position: list[dict[int, int]] = [
            {} for _ in range(len(counts) + 1)
        ]
        running_slots: dict[int, int] = {}
        for position in range(len(counts) - 1, -1, -1):
            count = int(counts[position])
            running_slots = dict(running_slots)
            running_slots[count] = running_slots.get(count, 0) + 1
            remaining_slots_by_position[position] = running_slots

        special_ids_by_count = {
            int(count): tuple(sorted(int(row.set_id) for row in rows))
            for count, rows in special_by_count.items()
        }

        visited_states: set[tuple[object, ...]] = set()
        nodes = leaves = witness_checks = feasible_leaves = rejected_leaves = 0
        score_pruned = physical_pruned = requirement_pruned = 0
        semantic_duplicate_leaves = 0

        def remaining_required_ids(count: int) -> tuple[int, ...]:
            return tuple(
                set_id
                for set_id in special_ids_by_count.get(int(count), ())
                if set_id not in selected_special_ids
            )

        def special_aware_remaining_bound(position: int) -> float | None:
            total = 0.0
            for count, slots in remaining_slots_by_position[position].items():
                required = remaining_required_ids(count)
                if len(required) > slots:
                    return None
                ordinary_needed = slots - len(required)
                if ordinary_needed <= 0:
                    continue
                available: list[float] = []
                seen: set[int] = set()
                for row in ordinary_candidates_by_count.get(int(count), ()):
                    set_id = int(row.set_id)
                    if set_id in used_ids or set_id in special_ids or set_id in seen:
                        continue
                    seen.add(set_id)
                    available.append(float(row.exact_delta))
                    if len(available) >= ordinary_needed:
                        break
                if len(available) < ordinary_needed:
                    return None
                total += sum(available[:ordinary_needed])
            return float(total)

        def semantic_key() -> tuple[tuple[object, ...], ...]:
            return tuple(selected_semantics)

        def equal_floor(position: int) -> int | None:
            if position <= 0 or position >= len(counts):
                return None
            if counts[position - 1] != counts[position]:
                return None
            return int(selected[position - 1].set_id)

        def prefix_state(position: int, score: float) -> tuple[object, ...]:
            still_relevant_used = tuple(
                sorted(set_id for set_id in used_ids if set_id in future_ids[position])
            )
            return (
                int(position),
                semantic_key(),
                float(score),
                still_relevant_used,
                tuple(sorted(selected_special_ids)),
                equal_floor(position),
            )

        def visit(position: int, score: float) -> None:
            nonlocal best, winners_by_semantic_key
            nonlocal nodes, leaves, witness_checks, feasible_leaves, rejected_leaves
            nonlocal score_pruned, physical_pruned, requirement_pruned
            nonlocal semantic_duplicate_leaves

            state = prefix_state(position, score)
            if state in visited_states:
                return
            visited_states.add(state)
            nodes += 1

            remaining_bound = special_aware_remaining_bound(position)
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
                    physical = tuple(selected_eligibilities)
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
            remaining_required_tuple = remaining_required_ids(count)
            remaining_required = set(remaining_required_tuple)
            remaining_slots = remaining_slots_by_position[position].get(count, 0)
            if len(remaining_required) > remaining_slots:
                requirement_pruned += 1
                return

            previous_equal_id = equal_floor(position)
            minimum_required = remaining_required_tuple[0] if remaining_required_tuple else None
            for row in rows_by_position[position]:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                if len(remaining_required) == remaining_slots and row.set_id not in remaining_required:
                    continue
                if minimum_required is not None and row.set_id > minimum_required:
                    continue

                selected.append(row)
                selected_semantics.append(semantic_atom_by_object_id[id(row)])
                selected_eligibilities.append(row.eligibility)
                used_ids.add(row.set_id)
                if row.special:
                    selected_special_ids.add(row.set_id)
                prefix = tuple(selected_eligibilities)
                if feasibility._is_possible_prevalidated(topology, prefix):
                    visit(position + 1, score + row.exact_delta)
                else:
                    physical_pruned += 1
                if row.special:
                    selected_special_ids.remove(row.set_id)
                used_ids.remove(row.set_id)
                selected_eligibilities.pop()
                selected_semantics.pop()
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
        return ExtremeMaxHealthSpecialSubsetWinner(
            topology=topology,
            special_pairs=pairs,
            best_ordinary_flat_delta=(None if best == float("-inf") else float(best)),
            realizations=tuple(winners),
            stats=owner._stats(
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


__all__ = ["ExtremeMaxResourceSemanticSpecialSubsetSearchService"]
