from __future__ import annotations

"""Report raw vs proof-reduced named-gear pressure without enumerating assignments."""

import argparse
from collections import Counter
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
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

_OBJECTIVES = ("max_magicka", "max_stamina")


def _pressure(topology, candidates_by_count: dict[int, tuple[object, ...]]) -> int:
    multiplicities = Counter(int(value) for value in topology.counts)
    total = 1
    for count, needed in multiplicities.items():
        available = len(candidates_by_count.get(count, ()))
        if available < needed:
            return 0
        total *= comb(available, needed)
    return int(total)


def _raw_candidates(relevance, eligibility) -> dict[int, tuple[int, ...]]:
    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
    values: dict[int, set[int]] = {}
    for evidence in relevance.evidence:
        if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        set_id = int(evidence.set_id)
        count = int(evidence.piece_count)
        physical = eligibility_by_id.get(set_id)
        if physical is None or not physical.has_physical_slot_evidence:
            continue
        if count > int(physical.max_equip_count):
            continue
        values.setdefault(count, set()).add(set_id)
    return {count: tuple(sorted(ids)) for count, ids in sorted(values.items())}


def _print_pressure(label: str, topology_catalog, candidates_by_count) -> None:
    rows = tuple(
        sorted(
            ((_pressure(row, candidates_by_count), row.signature) for row in topology_catalog.topologies),
            reverse=True,
        )
    )
    print(f"{label}_assignment_upper_bound_total={sum(value for value, _ in rows):,}")
    print(f"{label}_largest_topologies=")
    for value, signature in rows[:8]:
        print(f"  {signature}: {value:,}")


def _audit(database: Path, objective: str) -> None:
    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(objective, breakpoints)

    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    ordinary_service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )

    raw = _raw_candidates(relevance, eligibility)
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(topology)
    frontier, frontier_pruned = ordinary_service._frontier(reduced, representative_limit)
    ordinary, special = ordinary_service._candidates(frontier)

    print()
    print(objective.upper())
    print("raw_candidate_pairs_by_piece_count=")
    for count, rows in raw.items():
        print(f"  {count}-piece: {len(rows):,}")
    _print_pressure("raw", topology, raw)

    print(f"equivalent_breakpoints_pruned={equivalent_pruned:,}")
    print(f"frontier_breakpoints_pruned={frontier_pruned:,}")
    print(f"frontier_representative_limit={representative_limit:,}")
    print("ordinary_frontier_candidates_by_piece_count=")
    for count in sorted(ordinary):
        print(f"  {count}-piece: {len(ordinary[count]):,}")
    print(f"ordinary_exact_flat_candidate_pairs={sum(len(rows) for rows in ordinary.values()):,}")
    print(f"special_or_nonflat_candidate_pairs={len(special):,}")
    _print_pressure("ordinary_frontier", topology, ordinary)

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *tuple(topology.unresolved),
                *tuple(reduced.unresolved),
                *tuple(frontier.unresolved),
                *tuple(relevance.unresolved),
            )
            if str(item)
        )
    )
    print(f"unresolved_count={len(unresolved):,}")
    for item in unresolved[:10]:
        print(f"  unresolved: {item}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report post-equivalence/frontier named-gear pressure without exact search."
    )
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--objective", choices=_OBJECTIVES, action="append")
    args = parser.parse_args()

    database = Path(args.database)
    objectives = tuple(args.objective or _OBJECTIVES)
    print("EXTREME NAMED-GEAR FRONTIER PRESSURE")
    print(f"Database: {database}")
    print("This audit does not enumerate named-gear assignments or score builds.")
    for objective in objectives:
        _audit(database, objective)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
