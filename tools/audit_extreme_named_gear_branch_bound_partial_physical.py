from __future__ import annotations

"""Diagnose proof-safe partial physical pruning for Extreme named gear search.

This starts from the ordinary exact-flat branch-and-bound diagnostic, but adds a
necessary-condition physical feasibility test at every partial branch.  Future
unselected sets are treated as unconstrained, so a partial branch is pruned only
when the sets already chosen cannot fit *any* canonical physical realization of
the topology even under that optimistic assumption.

Diagnostic only.  Production search semantics are unchanged.
"""

import argparse
from dataclasses import dataclass
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_physical_slot_realization_service import (
    ExtremeGearPhysicalSlotRealizationService,
    ExtremeWeaponSlotShape,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from tools.audit_extreme_named_gear_objective_frontier import _frontier_reduced_breakpoints


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_ONE_HANDED_MAIN_TYPES = ("Axe", "Mace", "Sword", "Dagger")
_ONE_HANDED_OFF_TYPES = (*_ONE_HANDED_MAIN_TYPES, "Shield")
_TWO_HANDED_TYPES = (
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


@dataclass(frozen=True)
class _Candidate:
    set_id: int
    name: str
    count: int
    exact_delta: float


@dataclass
class _Stats:
    nodes: int = 0
    leaves: int = 0
    witness_checks: int = 0
    feasible_leaves: int = 0
    rejected_leaves: int = 0
    pruned_by_bound: int = 0
    pruned_by_partial_physical: int = 0
    partial_physical_checks: int = 0
    partial_physical_cache_hits: int = 0
    seed_leaves: int = 0
    seed_witness_checks: int = 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure partial physical pruning for Extreme named gear branch-and-bound."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_health")
    parser.add_argument("--top", type=int, default=1)
    return parser


def _exact_delta(reducer, evidence) -> float | None:
    if evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
        return None
    if evidence.search_state_rule is not None or evidence.candidate.unresolved:
        return None
    target_stats = ExtremeGearSetObjectiveService._target_stats(reducer.relevance.objective_key)
    effects = tuple(
        effect for effect in evidence.candidate.source_effects if effect.stat in target_stats
    )
    if not effects:
        return None
    if any(effect.operation is not EffectOperation.ADD for effect in effects):
        return None
    if any(effect.condition for effect in effects):
        return None
    return float(evidence.reviewed_delta)


def _selected_weapon_compatible(physical, selected_rows) -> bool:
    selected_count = len(selected_rows)
    indices = tuple(int(value) for value in physical.weapon_set_indices)

    if physical.weapon_shape is ExtremeWeaponSlotShape.NONE:
        return True

    if physical.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE:
        index = indices[0]
        if index >= selected_count:
            return True
        allowed = set(selected_rows[index].weapon_types)
        return any(item in allowed for item in _ONE_HANDED_MAIN_TYPES)

    if physical.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED:
        index = indices[0]
        if index >= selected_count:
            return True
        allowed = set(selected_rows[index].weapon_types)
        return any(item in allowed for item in _TWO_HANDED_TYPES)

    first, second = indices
    first_selected = first < selected_count
    second_selected = second < selected_count
    if not first_selected and not second_selected:
        return True

    if first_selected:
        first_allowed = set(selected_rows[first].weapon_types)
        if not any(item in first_allowed for item in _ONE_HANDED_MAIN_TYPES):
            return False
    if second_selected:
        second_allowed = set(selected_rows[second].weapon_types)
        if not any(item in second_allowed for item in _ONE_HANDED_OFF_TYPES):
            return False
    return True


def _partial_body_compatible(physical, selected_rows) -> bool:
    selected_count = len(selected_rows)
    if selected_count == 0:
        return True
    body_counts = tuple(int(value) for value in physical.body_jewelry_counts[:selected_count])
    return (
        ExtremeNamedGearSetRealizationService._body_assignments(
            body_counts,
            tuple(selected_rows),
        )
        is not None
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    objective = str(args.objective)

    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(objective, breakpoints)
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    equivalent, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology_catalog
    )
    frontier, frontier_pruned, frontier_eligible, _groups = _frontier_reduced_breakpoints(
        reducer=reducer,
        reduced=equivalent,
        representative_limit=representative_limit,
    )

    evidence_by_key = {
        (int(row.set_id), int(row.piece_count)): row for row in relevance.evidence
    }
    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}

    ordinary_by_count: dict[int, list[_Candidate]] = {}
    special_pairs: list[tuple[int, str, int]] = []
    for row in frontier.sets:
        physical = eligibility_by_id.get(int(row.set_id))
        if physical is None or not physical.has_physical_slot_evidence:
            continue
        for count in row.bonus_counts:
            evidence = evidence_by_key.get((int(row.set_id), int(count)))
            if evidence is None:
                continue
            delta = _exact_delta(reducer, evidence)
            if delta is None:
                special_pairs.append((int(row.set_id), str(row.name), int(count)))
                continue
            ordinary_by_count.setdefault(int(count), []).append(
                _Candidate(int(row.set_id), str(row.name), int(count), float(delta))
            )

    ordinary = {
        count: tuple(
            sorted(rows, key=lambda row: (-row.exact_delta, row.set_id, row.name.casefold()))
        )
        for count, rows in ordinary_by_count.items()
    }

    def pressure(topology) -> int:
        seen: dict[int, int] = {}
        for count in topology.counts:
            seen[int(count)] = seen.get(int(count), 0) + 1
        total = 1
        for count, needed in seen.items():
            available = len(ordinary.get(count, ()))
            if available < needed:
                return 0
            total *= comb(available, needed)
        return int(total)

    selected_topologies = tuple(
        sorted(
            topology_catalog.topologies,
            key=lambda row: (pressure(row), row.signature),
            reverse=True,
        )
    )[: max(1, int(args.top))]

    print("EXTREME PARTIAL-PHYSICAL BRANCH-AND-BOUND DIAGNOSTIC")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"frontier_eligible_breakpoints={frontier_eligible}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in ordinary.values())}")
    print(f"special_candidate_pairs_excluded={len(special_pairs)}")
    print(f"topologies_executed={len(selected_topologies)}")

    for topology in selected_topologies:
        counts = tuple(int(value) for value in topology.counts)
        candidate_rows = tuple(ordinary.get(count, ()) for count in counts)
        canonical_physicals = ExtremeGearPhysicalSlotRealizationService._witnesses_for_topology(topology)
        stats = _Stats()
        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=eligibility,
        )
        selected: list[_Candidate] = []
        used_ids: set[int] = set()
        best = float("-inf")
        partial_cache: dict[tuple[int, tuple[object, ...]], bool] = {}

        suffix_best = [0.0] * (len(counts) + 1)
        for pos in range(len(counts) - 1, -1, -1):
            rows = candidate_rows[pos]
            suffix_best[pos] = suffix_best[pos + 1] + max(
                (row.exact_delta for row in rows), default=float("-inf")
            )

        def partial_physical_possible() -> bool:
            if not selected:
                return True
            selected_rows = tuple(eligibility_by_id[row.set_id] for row in selected)
            shapes = tuple(realizer._eligibility_shape_cached(row) for row in selected_rows)
            key = (len(selected_rows), shapes)
            cached = partial_cache.get(key)
            if cached is not None:
                stats.partial_physical_cache_hits += 1
                return cached

            stats.partial_physical_checks += 1
            if ExtremeNamedGearSetRealizationService._violates_global_set_legality(
                counts[: len(selected_rows)],
                selected_rows,
            ):
                partial_cache[key] = False
                return False

            possible = False
            for physical in canonical_physicals:
                if not _selected_weapon_compatible(physical, selected_rows):
                    continue
                if not _partial_body_compatible(physical, selected_rows):
                    continue
                possible = True
                break
            partial_cache[key] = possible
            return possible

        def seed(position: int, score: float) -> bool:
            nonlocal best
            if position >= len(counts):
                stats.seed_leaves += 1
                physical = tuple(eligibility_by_id[row.set_id] for row in selected)
                stats.seed_witness_checks += 1
                if realizer._find_witness_cached(topology, physical) is None:
                    return False
                best = score
                return True

            previous_equal_id = None
            if position > 0 and counts[position - 1] == counts[position]:
                previous_equal_id = selected[position - 1].set_id
            for row in candidate_rows[position]:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                if partial_physical_possible() and seed(position + 1, score + row.exact_delta):
                    used_ids.remove(row.set_id)
                    selected.pop()
                    return True
                used_ids.remove(row.set_id)
                selected.pop()
            return False

        seed(0, 0.0)

        def visit(position: int, score: float) -> None:
            nonlocal best
            stats.nodes += 1
            if best != float("-inf") and score + suffix_best[position] < best - 1e-9:
                stats.pruned_by_bound += 1
                return
            if position >= len(counts):
                stats.leaves += 1
                physical = tuple(eligibility_by_id[row.set_id] for row in selected)
                stats.witness_checks += 1
                if realizer._find_witness_cached(topology, physical) is None:
                    stats.rejected_leaves += 1
                    return
                stats.feasible_leaves += 1
                if score > best:
                    best = score
                return

            previous_equal_id = None
            if position > 0 and counts[position - 1] == counts[position]:
                previous_equal_id = selected[position - 1].set_id
            for row in candidate_rows[position]:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                if partial_physical_possible():
                    visit(position + 1, score + row.exact_delta)
                else:
                    stats.pruned_by_partial_physical += 1
                used_ids.remove(row.set_id)
                selected.pop()

        visit(0, 0.0)
        best_text = "none" if best == float("-inf") else f"{best:.3f}"
        print(
            f"{topology.signature}: ordinary_pressure={pressure(topology)} "
            f"generic_physical_shapes={len(canonical_physicals)} "
            f"seed_leaves={stats.seed_leaves} seed_witness_checks={stats.seed_witness_checks} "
            f"nodes={stats.nodes} leaves={stats.leaves} witness_checks={stats.witness_checks} "
            f"feasible={stats.feasible_leaves} rejected={stats.rejected_leaves} "
            f"score_pruned={stats.pruned_by_bound} physical_pruned={stats.pruned_by_partial_physical} "
            f"partial_checks={stats.partial_physical_checks} partial_cache_hits={stats.partial_physical_cache_hits} "
            f"best_exact_flat_delta={best_text}"
        )

    unresolved = tuple(dict.fromkeys((*frontier.unresolved, *relevance.unresolved)))
    if unresolved:
        print("UNRESOLVED")
        for item in unresolved:
            print(f"  {item}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
