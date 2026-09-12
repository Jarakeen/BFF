from __future__ import annotations

"""Measure semantic duplication among production ordinary named-gear leaves.

This diagnostic invokes the real production branch-and-bound implementation and
wraps only the canonical witness lookup so we can count how many visited leaves
share the same identity-free physical eligibility tuple.  It changes no search
semantics and restores the original method before exiting.
"""

import argparse
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure semantic duplication among production Extreme named-gear leaves."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_health")
    parser.add_argument("--top", type=int, default=1)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    objective = str(args.objective)

    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(objective, breakpoints)

    service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology_catalog
    )
    frontier, frontier_pruned = service._frontier(reduced, representative_limit)
    candidates, special = service._candidates(frontier)

    def pressure(topology) -> int:
        needed_by_count: dict[int, int] = {}
        for count in topology.counts:
            needed_by_count[int(count)] = needed_by_count.get(int(count), 0) + 1
        total = 1
        for count, needed in needed_by_count.items():
            available = len(candidates.get(int(count), ()))
            if available < needed:
                return 0
            total *= comb(available, needed)
        return int(total)

    selected = tuple(
        sorted(
            topology_catalog.topologies,
            key=lambda row: (pressure(row), row.signature),
            reverse=True,
        )
    )[: max(1, int(args.top))]

    print("EXTREME PRODUCTION NAMED-GEAR LEAF SEMANTICS")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in candidates.values())}")
    print(f"special_candidate_pairs_excluded={len(special)}")
    print(f"topologies_executed={len(selected)}")

    original = ExtremeNamedGearSetCatalogRealizationService._find_witness_cached
    call_count = 0
    semantic_keys: set[tuple[object, ...]] = set()

    def wrapped(self, topology, selected_rows):
        nonlocal call_count
        call_count += 1
        semantic_keys.add(
            (
                topology.signature,
                tuple(self._eligibility_shape_cached(row) for row in selected_rows),
            )
        )
        return original(self, topology, selected_rows)

    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    ExtremeNamedGearSetCatalogRealizationService._find_witness_cached = wrapped
    try:
        for topology in selected:
            before_calls = call_count
            before_keys = len(semantic_keys)
            winner = service._search_topology(
                topology,
                candidates,
                frontier,
                feasibility=feasibility,
            )
            stats = winner.stats
            topology_calls = call_count - before_calls
            topology_unique = len(semantic_keys) - before_keys
            duplicate_calls = topology_calls - topology_unique
            ratio = (
                0.0
                if topology_calls == 0
                else 100.0 * duplicate_calls / topology_calls
            )
            best = (
                "none"
                if winner.best_exact_flat_delta is None
                else f"{winner.best_exact_flat_delta:.3f}"
            )
            print(
                f"{topology.signature}: ordinary_pressure={pressure(topology)} "
                f"nodes={stats.nodes} leaves={stats.leaves} "
                f"witness_calls={topology_calls} unique_semantic_leaf_classes={topology_unique} "
                f"duplicate_semantic_leaves={duplicate_calls} duplicate_percent={ratio:.2f} "
                f"winning_realizations={len(winner.realizations)} "
                f"best_exact_flat_delta={best}"
            )
    finally:
        ExtremeNamedGearSetCatalogRealizationService._find_witness_cached = original

    unresolved = tuple(
        dict.fromkeys(
            (
                *topology_catalog.unresolved,
                *frontier.unresolved,
                *relevance.unresolved,
            )
        )
    )
    if unresolved:
        print("UNRESOLVED")
        for item in unresolved:
            print(f"  {item}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
