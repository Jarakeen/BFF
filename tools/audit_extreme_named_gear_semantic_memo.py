from __future__ import annotations

"""Compare ordinary vs semantic-memo exact named-gear search on worst topologies."""

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
from services.extreme_max_resource_semantic_memo_search_service import (
    ExtremeMaxResourceSemanticMemoSearchService,
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

_OBJECTIVES = ("max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare baseline and semantic-memo Extreme named-gear search."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, required=True)
    parser.add_argument("--top", type=int, default=3)
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

    baseline = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    memo = ExtremeMaxResourceSemanticMemoSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology_catalog
    )
    frontier, _frontier_pruned = baseline._frontier(reduced, representative_limit)
    candidates, _special = baseline._candidates(frontier)

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

    print("EXTREME NAMED-GEAR SEMANTIC MEMO COMPARISON")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"topologies={len(selected)}")

    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    mismatch = False
    for topology in selected:
        ordinary = baseline._search_topology(
            topology,
            candidates,
            frontier,
            feasibility=feasibility,
        )
        optimized = memo._search_topology(
            topology,
            candidates,
            frontier,
            feasibility=feasibility,
        )

        ordinary_keys = {
            (
                row.set_ids,
                row.weapon_shape.value,
                tuple((item.slot, item.set_id, item.weapon_type) for item in row.assignments),
            )
            for row in ordinary.realizations
        }
        optimized_keys = {
            (
                row.set_ids,
                row.weapon_shape.value,
                tuple((item.slot, item.set_id, item.weapon_type) for item in row.assignments),
            )
            for row in optimized.realizations
        }
        same_value = ordinary.best_exact_flat_delta == optimized.best_exact_flat_delta
        # Concrete representative identity may differ inside a proven semantic class;
        # cardinality must still match because the contract retains one witness/class.
        same_tie_count = len(ordinary.realizations) == len(optimized.realizations)
        mismatch = mismatch or not (same_value and same_tie_count)

        base_nodes = ordinary.stats.nodes
        memo_nodes = optimized.stats.nodes
        node_reduction = 0.0 if base_nodes == 0 else 100.0 * (base_nodes - memo_nodes) / base_nodes
        base_leaves = ordinary.stats.leaves
        memo_leaves = optimized.stats.leaves
        leaf_reduction = 0.0 if base_leaves == 0 else 100.0 * (base_leaves - memo_leaves) / base_leaves

        print(
            f"{topology.signature}: pressure={pressure(topology)} "
            f"best={ordinary.best_exact_flat_delta} "
            f"same_value={same_value} same_tie_count={same_tie_count} "
            f"baseline_nodes={base_nodes} memo_nodes={memo_nodes} node_reduction={node_reduction:.2f}% "
            f"baseline_leaves={base_leaves} memo_leaves={memo_leaves} leaf_reduction={leaf_reduction:.2f}% "
            f"baseline_semantic_classes={ordinary.stats.semantic_leaf_classes} "
            f"memo_semantic_classes={optimized.stats.semantic_leaf_classes} "
            f"baseline_winners={len(ordinary_keys)} memo_winners={len(optimized_keys)}"
        )

    if mismatch:
        print("RESULT: MISMATCH - semantic memo must not be enabled in production")
        return 2
    print("RESULT: exact best values and semantic tie counts preserved for audited topologies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
