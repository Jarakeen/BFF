from __future__ import annotations

"""Measure the production Max Health special named-gear frontier on hot topologies.

The ordinary production branch has already been reduced aggressively. This diagnostic
measures the remaining special-set compositor using the same frontier, candidate lists,
distinct-ID bound, shared physical-feasibility cache, and semantic leaf collapse as the
record path. It intentionally does not run the full downstream armor/Mundus/food/potion
record search.
"""

import argparse
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
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthNamedGearCandidateSearchService,
)
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialNamedGearBranchService,
)
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure production Max Health special named-gear subset search."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--top", type=int, default=1)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "max_health", breakpoints
    )

    ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    composer = ExtremeMaxHealthNamedGearCandidateSearchService(
        ordinary_service=ordinary,
        eligibility=eligibility,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology_catalog
    )
    frontier, frontier_pruned = ordinary._frontier(reduced, representative_limit)
    ordinary_candidates, special_pairs = ordinary._candidates(frontier)
    classified = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(special_pairs)
    branches = tuple(classified.branches)

    def pressure(topology) -> int:
        needed_by_count: dict[int, int] = {}
        for count in topology.counts:
            needed_by_count[int(count)] = needed_by_count.get(int(count), 0) + 1
        total = 1
        for count, needed in needed_by_count.items():
            available = len(ordinary_candidates.get(int(count), ()))
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

    print("EXTREME MAX HEALTH SPECIAL NAMED-GEAR FRONTIER")
    print(f"Database: {database}")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in ordinary_candidates.values())}")
    print(f"special_candidate_pairs={len(special_pairs)}")
    print(f"classified_special_branches={len(branches)}")
    print(f"topologies_executed={len(selected)}")

    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    for topology in selected:
        subset_count = 0
        winning_subset_count = 0
        retained_realizations = 0
        nodes = leaves = witness_checks = feasible = rejected = 0
        score_pruned = physical_pruned = requirement_pruned = 0
        semantic_classes = semantic_duplicates = 0

        for size in range(1, len(branches) + 1):
            for subset in combinations(branches, size):
                subset_tuple = tuple(subset)
                if not composer._subset_fits_counts(topology, subset_tuple):
                    continue
                subset_count += 1
                winner = composer._search_subset(
                    topology=topology,
                    subset=subset_tuple,
                    ordinary_candidates_by_count=ordinary_candidates,
                    frontier=frontier,
                    feasibility=feasibility,
                )
                stats = winner.stats
                if winner.winner_found:
                    winning_subset_count += 1
                    retained_realizations += len(winner.realizations)
                nodes += stats.nodes
                leaves += stats.leaves
                witness_checks += stats.witness_checks
                feasible += stats.feasible_leaves
                rejected += stats.rejected_leaves
                score_pruned += stats.score_pruned
                physical_pruned += stats.physical_pruned
                requirement_pruned += stats.requirement_pruned
                semantic_classes += stats.semantic_leaf_classes
                semantic_duplicates += stats.semantic_duplicate_leaves

        print(
            f"{topology.signature}: ordinary_pressure={pressure(topology)} "
            f"legal_special_subsets={subset_count} winning_special_subsets={winning_subset_count} "
            f"nodes={nodes} leaves={leaves} witness_checks={witness_checks} "
            f"feasible={feasible} rejected={rejected} score_pruned={score_pruned} "
            f"physical_pruned={physical_pruned} requirement_pruned={requirement_pruned} "
            f"semantic_leaf_classes={semantic_classes} semantic_duplicate_leaves={semantic_duplicates} "
            f"retained_realizations={retained_realizations}"
        )

    unresolved = tuple(
        dict.fromkeys(
            (
                *topology_catalog.unresolved,
                *frontier.unresolved,
                *relevance.unresolved,
                *classified.unresolved,
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
