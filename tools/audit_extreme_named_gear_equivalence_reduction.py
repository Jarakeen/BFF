from __future__ import annotations

import argparse
from collections import Counter
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure proof-safe named-gear equivalence reduction before concrete "
            "gear-witness enumeration. This is diagnostic accounting only."
        )
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_health")
    return parser


def _candidate_ids_by_count(
    breakpoints: ExtremeGearSetBonusBreakpointCatalog,
    eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
) -> dict[int, tuple[int, ...]]:
    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
    values: dict[int, set[int]] = {}
    for breakpoint_set in breakpoints.sets:
        row = eligibility_by_id.get(int(breakpoint_set.set_id))
        if row is None or not row.has_physical_slot_evidence:
            continue
        for count in breakpoint_set.bonus_counts:
            if int(count) > int(row.max_equip_count):
                continue
            values.setdefault(int(count), set()).add(int(breakpoint_set.set_id))
    return {
        count: tuple(sorted(set_ids))
        for count, set_ids in sorted(values.items())
    }


def _upper_bound(
    topology: ExtremeGearSetCountTopology,
    candidate_ids_by_count: dict[int, tuple[int, ...]],
) -> int:
    multiplicities = Counter(int(value) for value in topology.counts)
    total = 1
    for count, needed in multiplicities.items():
        available = len(candidate_ids_by_count.get(count, ()))
        if available < needed:
            return 0
        total *= comb(available, needed)
    return int(total)


def _pressure(topology, candidate_ids_by_count):
    return tuple(
        sorted(
            (
                (_upper_bound(row, candidate_ids_by_count), row.signature)
                for row in topology.topologies
            ),
            reverse=True,
        )
    )


def _print_counts(label: str, rows: dict[int, tuple[int, ...]]) -> None:
    print(label)
    if not rows:
        print("  none")
        return
    for count, set_ids in rows.items():
        print(f"  {count}-piece: {len(set_ids)}")


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    objective = str(args.objective)

    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        objective,
        breakpoints,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )

    filtered = reducer._filtered_breakpoints()
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology
    )

    raw_ids = _candidate_ids_by_count(filtered, eligibility)
    reduced_ids = _candidate_ids_by_count(reduced, eligibility)
    raw_pressure = _pressure(topology, raw_ids)
    reduced_pressure = _pressure(topology, reduced_ids)

    print("EXTREME NAMED GEAR EQUIVALENCE REDUCTION")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"representative_limit_per_equivalence_class={representative_limit}")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print()
    _print_counts("before_reduction_candidate_sets_by_piece_count=", raw_ids)
    print(f"before_reduction_assignment_upper_bound={sum(value for value, _ in raw_pressure)}")
    print()
    _print_counts("after_reduction_candidate_sets_by_piece_count=", reduced_ids)
    print(f"after_reduction_assignment_upper_bound={sum(value for value, _ in reduced_pressure)}")
    print("after_reduction_largest_topologies=")
    for value, signature in reduced_pressure[:8]:
        print(f"  {signature}: {value}")
    if len(reduced_pressure) > 8:
        print(f"  ... {len(reduced_pressure) - 8} more topologies")

    unresolved = tuple(
        dict.fromkeys(
            (*filtered.unresolved, *reduced.unresolved, *relevance.unresolved)
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
