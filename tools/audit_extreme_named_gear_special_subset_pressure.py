from __future__ import annotations

"""Report metadata-only pressure for Extreme max-resource special gear subsets.

This audit does not execute special-subset recursion, score builds, or realize gear.
It composes the same proof-reduced ordinary frontier and classified special branches
used by production, then measures the ordinary filler combination upper bound after
each fixed special subset consumes topology positions and set identities.
"""

import argparse
from collections import Counter
from itertools import combinations
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
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)

_OBJECTIVES = ("max_magicka", "max_stamina")


def _fits(topology, subset) -> bool:
    available = Counter(int(value) for value in topology.counts)
    required = Counter(int(row.piece_count) for row in subset)
    return all(required[count] <= available[count] for count in required)


def _pressure(topology, subset, candidates_by_count) -> int:
    needed = Counter(int(value) for value in topology.counts)
    special_needed = Counter(int(row.piece_count) for row in subset)
    special_ids = {int(row.set_id) for row in subset}
    total = 1
    for count, slots in needed.items():
        ordinary_needed = int(slots) - int(special_needed.get(count, 0))
        if ordinary_needed < 0:
            return 0
        if ordinary_needed == 0:
            continue
        available_ids = {
            int(row.set_id)
            for row in candidates_by_count.get(int(count), ())
            if int(row.set_id) not in special_ids
        }
        if len(available_ids) < ordinary_needed:
            return 0
        total *= comb(len(available_ids), ordinary_needed)
    return int(total)


def _label(subset) -> str:
    return " + ".join(
        f"{row.set_name}({row.piece_count},{row.kind.value})" for row in subset
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure proof-reduced ordinary filler pressure under fixed Extreme special gear subsets."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_magicka")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    database = Path(args.database)
    objective = str(args.objective)
    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(objective, breakpoints)

    ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(topology)
    frontier, frontier_pruned = ordinary._frontier(reduced, representative_limit)
    candidates, special_pairs = ordinary._candidates(frontier)
    classified = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(special_pairs)

    print("EXTREME SPECIAL-SUBSET PRESSURE")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print("This audit does not execute special-subset recursion or score builds.")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in candidates.values())}")
    print(f"special_pairs={len(special_pairs)} classified={len(classified.branches)}")
    print("special_branches=")
    for row in classified.branches:
        conditions = ",".join(row.required_conditions) or "<none>"
        print(
            f"  id={row.set_id} name={row.set_name!r} pieces={row.piece_count} "
            f"kind={row.kind.value} value={row.value!r} condition={row.condition!r} "
            f"required_conditions={conditions} search_state_rule={getattr(row.search_state_rule, 'value', row.search_state_rule)!r}"
        )

    rows: list[tuple[int, str, str, int]] = []
    subset_count = 0
    topology_subset_count = 0
    branches = tuple(classified.branches)
    for size in range(1, len(branches) + 1):
        for subset in combinations(branches, size):
            subset_count += 1
            label = _label(subset)
            for top in topology.topologies:
                if not _fits(top, subset):
                    continue
                topology_subset_count += 1
                rows.append((_pressure(top, subset, candidates), top.signature, label, size))

    rows.sort(key=lambda item: (item[0], item[3], item[1], item[2]), reverse=True)
    print(f"nonempty_special_subsets={subset_count}")
    print(f"fitting_topology_subset_pairs={topology_subset_count}")
    print("largest_special_subset_filler_pressure=")
    for pressure, signature, label, size in rows[: max(1, int(args.top))]:
        print(f"  pressure={pressure:,} subset_size={size} topology={signature} :: {label}")
    if len(rows) > max(1, int(args.top)):
        print(f"  ... {len(rows) - max(1, int(args.top)):,} more fitting topology/subset pairs")

    unresolved = tuple(
        dict.fromkeys(
            (
                *tuple(topology.unresolved),
                *tuple(frontier.unresolved),
                *tuple(relevance.unresolved),
                *tuple(classified.unresolved),
            )
        )
    )
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved[:10]:
        print(f"  unresolved: {item}")
    if len(unresolved) > 10:
        print(f"  ... {len(unresolved) - 10} more")
    return 0 if not unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
