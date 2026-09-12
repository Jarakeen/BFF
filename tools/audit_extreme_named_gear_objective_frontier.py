from __future__ import annotations

"""Measure a proof-safe objective frontier for Extreme max-resource named gear.

This diagnostic starts from the exact-equivalence-reduced breakpoint catalog.  For
mechanic-complete ordinary max-resource candidates, the canonical objective service
has already reduced every supported requested-resource effect to an exact flat
``reviewed_delta``.  Percentage and conditional resource effects remain unresolved
there and are deliberately excluded from this reduction.

Within one piece count and one identical physical-slot eligibility shape, a lower
flat-resource candidate can never beat a higher one.  A legal active snapshot has
at most N set parts, so retaining the best N distinct named identities in each such
class preserves a replacement even when N-1 better identities are already consumed
elsewhere in the topology.  Unresolved candidates and search-space mutators remain
individually searchable.

This file is diagnostic accounting only.  It does not mutate the production search.
"""

import argparse
from collections import Counter
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
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
            "Measure a proof-safe exact flat-resource frontier after Extreme named-gear "
            "equivalence reduction. Diagnostic only."
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
    return {count: tuple(sorted(ids)) for count, ids in sorted(values.items())}


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


def _flat_frontier_descriptor(reducer, evidence, eligibility):
    if evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
        return None
    if evidence.search_state_rule is not None:
        return None
    if evidence.candidate.unresolved:
        return None
    if eligibility is None or not eligibility.has_physical_slot_evidence:
        return None

    target_stats = ExtremeGearSetObjectiveService._target_stats(
        reducer.relevance.objective_key
    )
    target_effects = tuple(
        effect for effect in evidence.candidate.source_effects if effect.stat in target_stats
    )
    if not target_effects:
        return None
    # Max-resource percentage/conditional mechanics are not considered exact flat
    # contributions by ExtremeGearSetObjectiveService.  Refuse them here too.
    if any(effect.operation is not EffectOperation.ADD for effect in target_effects):
        return None
    if any(effect.condition for effect in target_effects):
        return None

    return (
        int(evidence.piece_count),
        reducer._eligibility_signature(eligibility),
    ), float(evidence.reviewed_delta)


def _frontier_reduced_breakpoints(
    *,
    reducer: ExtremeObjectiveNamedGearSetCatalogRealizationService,
    reduced: ExtremeGearSetBonusBreakpointCatalog,
    representative_limit: int,
):
    evidence_by_key = {
        (int(row.set_id), int(row.piece_count)): row
        for row in reducer.relevance.evidence
    }
    eligibility_by_id = {int(row.set_id): row for row in reducer.eligibility.sets}

    groups: dict[tuple[object, ...], list[tuple[int, str, int, float]]] = {}
    eligible_pairs = 0
    for breakpoint_set in reduced.sets:
        for count in breakpoint_set.bonus_counts:
            pair = (int(breakpoint_set.set_id), int(count))
            evidence = evidence_by_key.get(pair)
            if evidence is None:
                continue
            descriptor = _flat_frontier_descriptor(
                reducer,
                evidence,
                eligibility_by_id.get(pair[0]),
            )
            if descriptor is None:
                continue
            key, delta = descriptor
            groups.setdefault(key, []).append(
                (pair[0], str(breakpoint_set.name), pair[1], float(delta))
            )
            eligible_pairs += 1

    limit = max(1, int(representative_limit))
    pruned_pairs: set[tuple[int, int]] = set()
    for members in groups.values():
        ordered = tuple(
            sorted(
                members,
                key=lambda item: (-item[3], item[0], item[1].casefold(), item[1]),
            )
        )
        for set_id, _name, count, _delta in ordered[limit:]:
            pruned_pairs.add((int(set_id), int(count)))

    output: list[ExtremeGearSetBonusBreakpoints] = []
    for breakpoint_set in reduced.sets:
        kept = tuple(
            int(count)
            for count in breakpoint_set.bonus_counts
            if (int(breakpoint_set.set_id), int(count)) not in pruned_pairs
        )
        output.append(
            ExtremeGearSetBonusBreakpoints(
                set_id=int(breakpoint_set.set_id),
                name=breakpoint_set.name,
                max_equip_count=int(breakpoint_set.max_equip_count),
                bonus_counts=kept,
                rejected_bonus_counts=tuple(breakpoint_set.rejected_bonus_counts),
            )
        )

    return (
        ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(output),
            unresolved=tuple(reduced.unresolved),
        ),
        len(pruned_pairs),
        eligible_pairs,
        len(groups),
    )


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

    equivalent_reduced, equivalent_pruned, representative_limit = (
        reducer.proof_reduced_breakpoints(topology)
    )
    frontier_reduced, frontier_pruned, frontier_eligible, frontier_groups = (
        _frontier_reduced_breakpoints(
            reducer=reducer,
            reduced=equivalent_reduced,
            representative_limit=representative_limit,
        )
    )

    before_ids = _candidate_ids_by_count(equivalent_reduced, eligibility)
    after_ids = _candidate_ids_by_count(frontier_reduced, eligibility)
    before_pressure = _pressure(topology, before_ids)
    after_pressure = _pressure(topology, after_ids)

    print("EXTREME NAMED GEAR OBJECTIVE FRONTIER DIAGNOSTIC")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"representative_limit={representative_limit}")
    print(f"equivalent_breakpoints_already_pruned={equivalent_pruned}")
    print(f"frontier_eligible_breakpoints={frontier_eligible}")
    print(f"frontier_legality_groups={frontier_groups}")
    print(f"flat_objective_breakpoints_prunable={frontier_pruned}")
    print()
    _print_counts("before_frontier_candidate_sets_by_piece_count=", before_ids)
    print(f"before_frontier_assignment_upper_bound={sum(value for value, _ in before_pressure)}")
    print()
    _print_counts("after_frontier_candidate_sets_by_piece_count=", after_ids)
    print(f"after_frontier_assignment_upper_bound={sum(value for value, _ in after_pressure)}")
    print("after_frontier_largest_topologies=")
    for value, signature in after_pressure[:8]:
        print(f"  {signature}: {value}")
    if len(after_pressure) > 8:
        print(f"  ... {len(after_pressure) - 8} more topologies")

    unresolved = tuple(
        dict.fromkeys(
            (
                *equivalent_reduced.unresolved,
                *frontier_reduced.unresolved,
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
