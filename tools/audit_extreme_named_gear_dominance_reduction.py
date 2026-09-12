from __future__ import annotations

"""Measure a proof-safe dominance reduction for Extreme max-resource named gear.

This diagnostic starts from the already proof-safe equivalence-reduced breakpoint
catalog. It then asks a narrower question: can a fully resolved candidate be
replaced by enough strictly better candidates with identical piece cost, physical
slot legality, objective-effect mechanic shape, and condition semantics?

A legal active-snapshot topology contains at most N distinct set identities, where
N is the maximum number of set parts across the topology catalog. A candidate is
therefore dominance-prunable only when at least N *distinct* named candidates in
its exact legality/mechanic class componentwise dominate its requested-objective
effect vector. Even if N-1 better identities are already occupied elsewhere in the
build, one legal dominating replacement remains available.

This file is diagnostic accounting only. It does not mutate the production search.
"""

import argparse
from collections import Counter
from math import comb
from pathlib import Path
import sys
from typing import Any

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
_DOMINANCE_OPERATIONS = {EffectOperation.ADD, EffectOperation.ADD_PERCENT}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure proof-safe componentwise dominance pressure after Extreme "
            "named-gear equivalence reduction. Diagnostic only."
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


def _mechanic_shape(reducer, effect: Any) -> tuple[Any, ...]:
    signature = reducer._effect_signature(effect)
    return (*signature[:2], *signature[3:])


def _dominance_descriptor(reducer, evidence, eligibility):
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
    effects = tuple(
        effect
        for effect in evidence.candidate.source_effects
        if effect.stat in target_stats
    )
    if not effects:
        return None
    if any(effect.operation not in _DOMINANCE_OPERATIONS for effect in effects):
        return None

    rows = tuple(
        sorted(
            ((_mechanic_shape(reducer, effect), float(effect.value)) for effect in effects),
            key=lambda item: (item[0], item[1]),
        )
    )
    shape = tuple(item[0] for item in rows)
    values = tuple(item[1] for item in rows)
    return (
        int(evidence.piece_count),
        reducer._eligibility_signature(eligibility),
        shape,
    ), values


def _strictly_componentwise_dominates(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> bool:
    if len(left) != len(right):
        return False
    return all(a >= b - 1e-12 for a, b in zip(left, right)) and any(
        a > b + 1e-12 for a, b in zip(left, right)
    )


def _dominance_reduced_breakpoints(
    *,
    reducer: ExtremeObjectiveNamedGearSetCatalogRealizationService,
    reduced: ExtremeGearSetBonusBreakpointCatalog,
    representative_limit: int,
) -> tuple[ExtremeGearSetBonusBreakpointCatalog, int, int]:
    evidence_by_key = {
        (int(row.set_id), int(row.piece_count)): row
        for row in reducer.relevance.evidence
    }
    eligibility_by_id = {
        int(row.set_id): row
        for row in reducer.eligibility.sets
    }

    groups: dict[tuple[Any, ...], list[tuple[int, int, tuple[float, ...]]]] = {}
    eligible_pairs = 0
    for breakpoint_set in reduced.sets:
        for count in breakpoint_set.bonus_counts:
            pair = (int(breakpoint_set.set_id), int(count))
            evidence = evidence_by_key.get(pair)
            if evidence is None:
                continue
            descriptor = _dominance_descriptor(
                reducer,
                evidence,
                eligibility_by_id.get(int(breakpoint_set.set_id)),
            )
            if descriptor is None:
                continue
            key, values = descriptor
            groups.setdefault(key, []).append((pair[0], pair[1], values))
            eligible_pairs += 1

    pruned_pairs: set[tuple[int, int]] = set()
    limit = max(1, int(representative_limit))
    for members in groups.values():
        for set_id, count, values in members:
            dominating_ids = {
                int(other_id)
                for other_id, _other_count, other_values in members
                if int(other_id) != int(set_id)
                and _strictly_componentwise_dominates(other_values, values)
            }
            if len(dominating_ids) >= limit:
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
    dominance_reduced, dominance_pruned, dominance_eligible = (
        _dominance_reduced_breakpoints(
            reducer=reducer,
            reduced=equivalent_reduced,
            representative_limit=representative_limit,
        )
    )

    before_ids = _candidate_ids_by_count(equivalent_reduced, eligibility)
    after_ids = _candidate_ids_by_count(dominance_reduced, eligibility)
    before_pressure = _pressure(topology, before_ids)
    after_pressure = _pressure(topology, after_ids)

    print("EXTREME NAMED GEAR DOMINANCE REDUCTION DIAGNOSTIC")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"representative_limit={representative_limit}")
    print(f"equivalent_breakpoints_already_pruned={equivalent_pruned}")
    print(f"dominance_eligible_breakpoints={dominance_eligible}")
    print(f"strictly_dominated_breakpoints_prunable={dominance_pruned}")
    print()
    _print_counts("before_dominance_candidate_sets_by_piece_count=", before_ids)
    print(
        "before_dominance_assignment_upper_bound="
        f"{sum(value for value, _ in before_pressure)}"
    )
    print()
    _print_counts("after_dominance_candidate_sets_by_piece_count=", after_ids)
    print(
        "after_dominance_assignment_upper_bound="
        f"{sum(value for value, _ in after_pressure)}"
    )
    print("after_dominance_largest_topologies=")
    for value, signature in after_pressure[:8]:
        print(f"  {signature}: {value}")
    if len(after_pressure) > 8:
        print(f"  ... {len(after_pressure) - 8} more topologies")

    unresolved = tuple(
        dict.fromkeys(
            (
                *equivalent_reduced.unresolved,
                *dominance_reduced.unresolved,
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
