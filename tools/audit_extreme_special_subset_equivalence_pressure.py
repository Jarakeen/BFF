from __future__ import annotations

"""Measure proof-safe equivalence opportunities across Max Resource special-subset searches.

This diagnostic does not change search behavior. It groups fitting topology/special-subset
pairs only when the exact ordinary filler problem sees the same structural constraints:

* topology counts/unused units;
* special breakpoint-count multiset;
* special physical eligibility shapes at each required breakpoint;
* special identities that actually overlap an ordinary candidate domain.

Mechanic identity is deliberately NOT discarded. The report only estimates how many
ordinary filler searches could be shared while distinct special mechanics remain attached
for later canonical execution.
"""

import argparse
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_ordinary_named_gear_search_service import ExtremeMaxResourceOrdinaryNamedGearSearchService
from services.extreme_max_resource_semantic_memo_search_service import ExtremeMaxResourceSemanticMemoSearchService
from services.extreme_max_resource_special_named_gear_branch_service import ExtremeMaxResourceSpecialNamedGearBranchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_objective_named_gear_set_catalog_realization_service import ExtremeObjectiveNamedGearSetCatalogRealizationService


OBJECTIVES = ("max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=OBJECTIVES, default="max_magicka")
    return parser


def _physical_shape(row) -> tuple[object, ...]:
    return (
        str(row.category or "").strip().casefold(),
        int(row.max_equip_count),
        tuple(row.armor_slots),
        tuple(row.jewelry_slots),
        tuple(row.weapon_types),
        tuple(int(value) for value in row.other_equip_types),
    )


def _subset_fits_counts(topology, subset) -> bool:
    available = Counter(int(value) for value in topology.counts)
    needed = Counter(int(row.piece_count) for row in subset)
    return all(available[count] >= amount for count, amount in needed.items())


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(args.objective, breakpoints)

    ordinary_base = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    ordinary = ExtremeMaxResourceSemanticMemoSearchService(
        breakpoints=ordinary_base.breakpoints,
        eligibility=ordinary_base.eligibility,
        relevance=ordinary_base.relevance,
    )

    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(topology_catalog)
    frontier, _frontier_pruned = ordinary._frontier(reduced, representative_limit)
    ordinary_candidates, special_pairs = ordinary._candidates(frontier)
    classified = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(special_pairs)

    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
    ordinary_ids_by_count = {
        int(count): frozenset(int(row.set_id) for row in rows)
        for count, rows in ordinary_candidates.items()
    }
    branches = tuple(classified.branches)
    if classified.unresolved:
        print("UNRESOLVED")
        for item in classified.unresolved:
            print(f"  {item}")
        return 2

    raw_pairs = 0
    classes: dict[tuple[object, ...], list[tuple[str, tuple[int, ...]]]] = defaultdict(list)

    for topology in topology_catalog.topologies:
        topology_counts = tuple(int(value) for value in topology.counts)
        for size in range(1, len(branches) + 1):
            for subset in combinations(branches, size):
                if not _subset_fits_counts(topology, subset):
                    continue
                raw_pairs += 1

                special_rows = []
                actual_excluded_by_count: dict[int, list[int]] = defaultdict(list)
                invalid = False
                for branch in subset:
                    physical = eligibility_by_id.get(int(branch.set_id))
                    if physical is None or not physical.has_physical_slot_evidence:
                        invalid = True
                        break
                    count = int(branch.piece_count)
                    set_id = int(branch.set_id)
                    if set_id in ordinary_ids_by_count.get(count, frozenset()):
                        actual_excluded_by_count[count].append(set_id)
                    special_rows.append((count, _physical_shape(physical)))
                if invalid:
                    continue

                exclusion_signature = tuple(
                    (count, tuple(sorted(ids)))
                    for count, ids in sorted(actual_excluded_by_count.items())
                )
                structural_signature = (
                    topology_counts,
                    int(topology.unused_units),
                    tuple(sorted(special_rows, key=repr)),
                    exclusion_signature,
                )
                classes[structural_signature].append(
                    (
                        topology.signature,
                        tuple(sorted(int(branch.set_id) for branch in subset)),
                    )
                )

    class_sizes = sorted((len(rows), signature, rows) for signature, rows in classes.items())
    reusable_classes = [row for row in class_sizes if row[0] > 1]
    represented_pairs = sum(size for size, _signature, _rows in reusable_classes)

    print("EXTREME SPECIAL SUBSET EQUIVALENCE PRESSURE")
    print(f"objective={args.objective}")
    print(f"special_branches={len(branches)}")
    print(f"raw_fitting_topology_subset_pairs={raw_pairs}")
    print(f"exact_structural_classes={len(classes)}")
    print(f"reusable_classes={len(reusable_classes)}")
    print(f"pairs_in_reusable_classes={represented_pairs}")
    print(f"maximum_class_size={max((size for size, _s, _r in class_sizes), default=0)}")

    print("\nLARGEST REUSABLE CLASSES")
    for size, signature, rows in sorted(reusable_classes, reverse=True, key=lambda row: row[0])[:20]:
        topology_counts, unused, special_shapes, exclusions = signature
        print(f"size={size} topology={topology_counts}|unused:{unused}")
        print(f"  special_shapes={special_shapes}")
        print(f"  ordinary_domain_exclusions={exclusions}")
        print(f"  examples={rows[:5]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
