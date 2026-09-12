from __future__ import annotations

"""Measure the actual production ordinary named-gear branch-and-bound path.

Unlike the earlier exploratory diagnostics, this tool does not duplicate the DFS.
It builds the canonical Max-resource denominator, selects the highest-pressure
requested topologies, then invokes the production ordinary search service directly.
This keeps reported node/prune counts synchronized with the code used by the record
engine.
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
        description="Measure the production Extreme ordinary named-gear branch-and-bound path."
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

    print("EXTREME PRODUCTION ORDINARY NAMED-GEAR BRANCH-AND-BOUND")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in candidates.values())}")
    print(f"special_candidate_pairs_excluded={len(special)}")
    print(f"topologies_executed={len(selected)}")

    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    for topology in selected:
        winner = service._search_topology(
            topology,
            candidates,
            frontier,
            feasibility=feasibility,
        )
        stats = winner.stats
        best = (
            "none"
            if winner.best_exact_flat_delta is None
            else f"{winner.best_exact_flat_delta:.3f}"
        )
        print(
            f"{topology.signature}: ordinary_pressure={pressure(topology)} "
            f"nodes={stats.nodes} leaves={stats.leaves} "
            f"witness_checks={stats.witness_checks} feasible={stats.feasible_leaves} "
            f"rejected={stats.rejected_leaves} score_pruned={stats.score_pruned} "
            f"physical_pruned={stats.physical_pruned} "
            f"best_exact_flat_delta={best}"
        )

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
