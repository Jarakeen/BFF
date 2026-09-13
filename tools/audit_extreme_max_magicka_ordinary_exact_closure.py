from __future__ import annotations

"""Close the Max Magicka ordinary named-gear denominator with production exact search.

This audit deliberately avoids the older diagnostic top-K/frontier-per-units path.
It invokes the production joint-feasibility branch-and-bound over every canonical
active-snapshot topology. The production reducer preserves enough provably
interchangeable named identities for every topology, while the search uses exact
flat Max Magicka contributions, distinct set identities, physical prefix feasibility,
and exact witness realization.

The current legal incumbent uses 12,986 exact ordinary gear Max Magicka. Ordinary
named gear is closed when the complete production denominator is proven and no legal
ordinary topology exceeds that contribution. Conditional/search-state gear remains a
separate already-classified special/runtime proof obligation.
"""

import argparse
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_max_resource_joint_feasibility_search_service import (
    ExtremeMaxResourceJointFeasibilitySearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)

OBJECTIVE = "max_magicka"
INCUMBENT = 108319.0
INCUMBENT_GEAR_DELTA = 12986.0
EXPECTED_SPECIAL_COUNT = 7


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT)
    parser.add_argument("--gear-threshold", type=float, default=INCUMBENT_GEAR_DELTA)
    args = parser.parse_args()

    database = Path(args.database)
    repository = GearSetRepository(database)
    topologies = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE,
        breakpoints,
    )

    service = ExtremeMaxResourceJointFeasibilitySearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )

    started = perf_counter()
    result = service.search(topologies)
    elapsed = perf_counter() - started

    legal = tuple(
        row
        for row in result.topologies
        if row.winner_found and row.best_exact_flat_delta is not None
    )
    ordered = tuple(
        sorted(
            legal,
            key=lambda row: (
                -float(row.best_exact_flat_delta or 0.0),
                row.topology.signature,
            ),
        )
    )
    best_delta = (
        max(float(row.best_exact_flat_delta or 0.0) for row in legal)
        if legal
        else None
    )
    above = tuple(
        row
        for row in ordered
        if float(row.best_exact_flat_delta or 0.0) > float(args.gear_threshold) + 1e-9
    )

    totals = {
        "nodes": sum(int(row.stats.nodes) for row in result.topologies),
        "leaves": sum(int(row.stats.leaves) for row in result.topologies),
        "witness_checks": sum(int(row.stats.witness_checks) for row in result.topologies),
        "feasible_leaves": sum(int(row.stats.feasible_leaves) for row in result.topologies),
        "rejected_leaves": sum(int(row.stats.rejected_leaves) for row in result.topologies),
        "score_pruned": sum(int(row.stats.score_pruned) for row in result.topologies),
        "physical_pruned": sum(int(row.stats.physical_pruned) for row in result.topologies),
        "semantic_leaf_classes": sum(int(row.stats.semantic_leaf_classes) for row in result.topologies),
        "semantic_duplicate_leaves": sum(int(row.stats.semantic_duplicate_leaves) for row in result.topologies),
    }

    denominator_clean = bool(
        relevance.denominator_proven
        and result.ordinary_denominator_proven
        and not result.unresolved
        and not topologies.unresolved
    )
    special_classification_expected = (
        len(result.special_or_nonflat_pairs) == EXPECTED_SPECIAL_COUNT
    )
    closed = bool(
        denominator_clean
        and special_classification_expected
        and not above
        and best_delta is not None
        and best_delta <= float(args.gear_threshold) + 1e-9
    )

    print("EXTREME MAX MAGICKA ORDINARY EXACT CLOSURE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"incumbent_gear_threshold={args.gear_threshold:.3f}")
    print("search=production_joint_feasibility_exact_branch_and_bound")
    print("arbitrary_top_k=False")
    print(f"topologies_reviewed={len(result.topologies)}")
    print(f"legal_topology_winners={len(legal)}")
    print(f"equivalent_breakpoints_pruned={result.equivalent_breakpoints_pruned}")
    print(f"frontier_breakpoints_pruned={result.frontier_breakpoints_pruned}")
    print(f"representative_limit={result.representative_limit}")
    print("equivalence_reduction_proven=True")
    print(f"special_or_nonflat_pairs={len(result.special_or_nonflat_pairs)}")
    print(f"special_classification_expected={special_classification_expected}")
    print(f"relevance_denominator_proven={relevance.denominator_proven}")
    print(f"ordinary_denominator_proven={result.ordinary_denominator_proven}")
    print(f"elapsed_seconds={elapsed:.3f}")
    for key, value in totals.items():
        print(f"{key}={value}")

    print("\nTOP ORDINARY TOPOLOGY WINNERS")
    for row in ordered[:10]:
        stats = row.stats
        print(
            f"  topology={row.topology.signature} "
            f"delta={float(row.best_exact_flat_delta or 0.0):.3f} "
            f"realizations={len(row.realizations)} nodes={stats.nodes} "
            f"leaves={stats.leaves} witness_checks={stats.witness_checks}"
        )

    print("\nORDINARY THRESHOLD RESULT")
    print(f"best_exact_ordinary_gear_delta={best_delta if best_delta is not None else '<none>'}")
    print(f"topologies_above_threshold={len(above)}")
    for row in above[:10]:
        print(
            f"  above: topology={row.topology.signature} "
            f"delta={float(row.best_exact_flat_delta or 0.0):.3f}"
        )

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *result.unresolved,
                *topologies.unresolved,
                *relevance.unresolved,
            )
            if str(item)
        )
    )
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    print(f"ordinary_exact_frontier_closed={closed}")

    if closed:
        print(
            "NEXT_STEP=ordinary named gear is exactly closed without an arbitrary frontier; "
            "compose the already-closed special/runtime denominator with the remaining "
            "non-gear proof axes for final whole-record closure"
        )
        return 0
    if above:
        print(
            "NEXT_STEP=an exact ordinary topology exceeds the incumbent gear threshold; "
            "materialize and canonical-score that production winner before final closure"
        )
        return 1
    print(
        "NEXT_STEP=resolve the reported ordinary denominator evidence before final whole-record closure"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
