from __future__ import annotations

"""Physically realize the reduced Weapon Damage + Max Resource named-gear frontier.

This audit consumes the Pareto + unresolved breakpoint pool from
``audit_extreme_weapon_damage_joint_named_gear_frontier`` and reuses the canonical
Extreme topology, slot-eligibility, and exact named-set witness services.

Mechanic-complete realizations are scored on the same equipped state for reviewed
Weapon Damage, Max Magicka, and Max Stamina set-bonus deltas. Realizations that
contain any unresolved breakpoint are retained as proof blockers and are never
promoted into the mechanic-complete Pareto frontier.

This remains a gear-layer diagnostic. Whole-build base resources, jewelry traits,
Mundus, CP, weapons, external named buffs, and Class Mastery are deliberately not
mixed in here.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalog,
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_weapon_damage_joint_named_gear_frontier import (
    _JointBreakpoint,
    _joint_rows,
    _pareto,
)

DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class _RealizedScore:
    topology_signature: str
    set_names: tuple[str, ...]
    set_ids: tuple[int, ...]
    counts: tuple[int, ...]
    weapon_shape: str
    weapon_damage: float
    max_magicka: float
    max_stamina: float
    unresolved: tuple[str, ...]

    @property
    def higher_resource(self) -> float:
        return max(self.max_magicka, self.max_stamina)

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved

    @property
    def signature(self) -> tuple:
        return (
            self.set_ids,
            self.counts,
            self.weapon_shape,
        )


def _survivor_rows(repository: GearSetRepository):
    breakpoints, _catalogs, rows = _joint_rows(repository)
    pareto = _pareto(rows)
    unresolved = tuple(row for row in rows if row.unresolved)
    survivor_by_key = {
        (int(row.set_id), int(row.piece_count)): row
        for row in (*pareto, *unresolved)
    }
    return breakpoints, pareto, unresolved, survivor_by_key


def _filtered_breakpoints(
    breakpoints,
    survivor_by_key: dict[tuple[int, int], _JointBreakpoint],
) -> ExtremeGearSetBonusBreakpointCatalog:
    counts_by_set: dict[int, set[int]] = {}
    for set_id, piece_count in survivor_by_key:
        counts_by_set.setdefault(int(set_id), set()).add(int(piece_count))

    rows = []
    unresolved = []
    for row in breakpoints.sets:
        wanted = counts_by_set.get(int(row.set_id))
        if not wanted:
            continue
        retained_counts = tuple(count for count in row.bonus_counts if int(count) in wanted)
        if not retained_counts:
            unresolved.append(
                f"{row.name}: reduced survivor pool has no canonical retained breakpoint count"
            )
            continue
        rows.append(replace(row, bonus_counts=retained_counts))

    known_ids = {int(row.set_id) for row in rows}
    for set_id in sorted(counts_by_set):
        if set_id not in known_ids:
            unresolved.append(f"Survivor set id {set_id} missing from canonical breakpoint catalog")

    return ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(rows),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def _filtered_eligibility(
    survivor_by_key: dict[tuple[int, int], _JointBreakpoint],
) -> ExtremeNamedGearSetSlotEligibilityCatalog:
    raw = ExtremeNamedGearSetSlotEligibilityService(DATABASE).build()
    survivor_ids = {int(set_id) for set_id, _count in survivor_by_key}
    names_by_id: dict[int, str] = {}
    for row in survivor_by_key.values():
        names_by_id.setdefault(int(row.set_id), str(row.set_name))

    rows = tuple(row for row in raw.sets if int(row.set_id) in survivor_ids)
    by_id = {int(row.set_id): row for row in rows}
    unresolved: list[str] = []

    for set_id in sorted(survivor_ids):
        row = by_id.get(set_id)
        name = names_by_id.get(set_id, str(set_id))
        if row is None:
            unresolved.append(f"{name}: no canonical named-set slot eligibility row")
            continue
        if not row.has_physical_slot_evidence:
            unresolved.append(f"{name}: no canonical physical slot evidence")

    survivor_names = tuple(name.casefold() for name in names_by_id.values())
    for message in raw.unresolved:
        folded = str(message).casefold()
        if any(name and name in folded for name in survivor_names):
            unresolved.append(str(message))

    return ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=rows,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def _filtered_topologies(
    repository: GearSetRepository,
    breakpoints: ExtremeGearSetBonusBreakpointCatalog,
) -> ExtremeGearSetTopologyCatalog:
    raw = ExtremeGearSetTopologyCatalogService(repository).build()
    candidate_counts = {
        int(count)
        for row in breakpoints.sets
        for count in row.bonus_counts
    }
    candidates_per_count = {
        count: sum(1 for row in breakpoints.sets if count in row.bonus_counts)
        for count in candidate_counts
    }

    rows = []
    for topology in raw.topologies:
        counts = tuple(int(value) for value in topology.counts)
        if not counts:
            continue
        if any(count not in candidate_counts for count in counts):
            continue
        feasible = True
        for count in set(counts):
            if counts.count(count) > candidates_per_count.get(count, 0):
                feasible = False
                break
        if feasible:
            rows.append(topology)

    return ExtremeGearSetTopologyCatalog(
        sets=tuple(row for row in raw.sets if int(row.set_id) in {int(item.set_id) for item in breakpoints.sets}),
        topologies=tuple(rows),
        unresolved=tuple(breakpoints.unresolved),
        active_snapshot_units=raw.active_snapshot_units,
        physical_slot_realization_proven=False,
    )


def _score_realization(witness, survivor_by_key) -> _RealizedScore:
    weapon_damage = 0.0
    max_magicka = 0.0
    max_stamina = 0.0
    unresolved: list[str] = []

    for set_id, set_name, count in zip(witness.set_ids, witness.set_names, witness.counts):
        row = survivor_by_key.get((int(set_id), int(count)))
        if row is None:
            unresolved.append(f"{set_name} {count}pc: missing reduced joint-breakpoint evidence")
            continue
        weapon_damage += float(row.weapon_damage)
        max_magicka += float(row.max_magicka)
        max_stamina += float(row.max_stamina)
        unresolved.extend(row.unresolved)

    return _RealizedScore(
        topology_signature=str(witness.topology_signature),
        set_names=tuple(str(value) for value in witness.set_names),
        set_ids=tuple(int(value) for value in witness.set_ids),
        counts=tuple(int(value) for value in witness.counts),
        weapon_shape=str(getattr(witness.weapon_shape, "value", witness.weapon_shape)),
        weapon_damage=float(weapon_damage),
        max_magicka=float(max_magicka),
        max_stamina=float(max_stamina),
        unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
    )


def _dominates(left: _RealizedScore, right: _RealizedScore) -> bool:
    ge = (
        left.weapon_damage >= right.weapon_damage - 1e-9
        and left.max_magicka >= right.max_magicka - 1e-9
        and left.max_stamina >= right.max_stamina - 1e-9
    )
    gt = (
        left.weapon_damage > right.weapon_damage + 1e-9
        or left.max_magicka > right.max_magicka + 1e-9
        or left.max_stamina > right.max_stamina + 1e-9
    )
    return ge and gt


def _realized_pareto(rows: tuple[_RealizedScore, ...]) -> tuple[_RealizedScore, ...]:
    complete = tuple(row for row in rows if row.mechanic_complete)

    # Multiple slot witnesses may have identical reviewed objective coordinates.
    # Keep one stable representative before the Pareto comparison.
    representative: dict[tuple[float, float, float], _RealizedScore] = {}
    for row in complete:
        key = (row.weapon_damage, row.max_magicka, row.max_stamina)
        current = representative.get(key)
        if current is None or row.signature < current.signature:
            representative[key] = row
    unique = tuple(representative.values())

    frontier = tuple(
        row
        for row in unique
        if not any(other is not row and _dominates(other, row) for other in unique)
    )
    return tuple(
        sorted(
            frontier,
            key=lambda row: (
                -row.weapon_damage,
                -row.higher_resource,
                -row.max_magicka,
                -row.max_stamina,
                row.counts,
                tuple(name.casefold() for name in row.set_names),
            ),
        )
    )


def main() -> int:
    repository = GearSetRepository(DATABASE)
    original_breakpoints, pareto_rows, unresolved_rows, survivor_by_key = _survivor_rows(repository)
    breakpoints = _filtered_breakpoints(original_breakpoints, survivor_by_key)
    eligibility = _filtered_eligibility(survivor_by_key)
    topologies = _filtered_topologies(repository, breakpoints)

    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    scores: list[_RealizedScore] = []
    assignments_considered = 0
    assignments_rejected = 0
    topology_rows_realized = 0

    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        assignments_considered += int(result.assignments_considered)
        assignments_rejected += int(result.assignments_rejected)
        if result.realizations:
            topology_rows_realized += 1
        scores.extend(_score_realization(witness, survivor_by_key) for witness in result.realizations)

    scored = tuple(scores)
    complete = tuple(row for row in scored if row.mechanic_complete)
    unresolved_realized = tuple(row for row in scored if not row.mechanic_complete)
    frontier = _realized_pareto(scored)

    print("EXTREME WEAPON DAMAGE + MAX RESOURCE PHYSICAL NAMED-GEAR FRONTIER")
    print(f"database={DATABASE}")
    print("scope=reduced Pareto plus unresolved canonical named-set breakpoint pool")
    print("exact_physical_slot_witnesses=True")
    print("whole_build_same_resource_proof=False")
    print()

    print("REDUCED INPUT")
    print(f"mechanic_complete_breakpoint_pareto={len(pareto_rows)}")
    print(f"unresolved_breakpoints_retained={len(unresolved_rows)}")
    print(f"joint_breakpoint_survivors={len(survivor_by_key)}")
    print(f"survivor_set_identities={len(breakpoints.sets)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"survivor_slot_eligibility_rows={len(eligibility.sets)}")
    print(f"survivor_slot_eligibility_unresolved={len(eligibility.unresolved)}")
    for message in eligibility.unresolved:
        print(f"  eligibility_unresolved: {message}")
    print()

    print("PHYSICAL REALIZATION")
    print(f"assignments_considered={assignments_considered}")
    print(f"assignments_rejected={assignments_rejected}")
    print(f"physical_realizations={len(scored)}")
    print(f"topologies_with_realizations={topology_rows_realized}")
    print(f"mechanic_complete_realizations={len(complete)}")
    print(f"unresolved_realizations_retained={len(unresolved_realized)}")
    print()

    print("MECHANIC-COMPLETE PHYSICAL PARETO STATES")
    print(f"physical_pareto_count={len(frontier)}")
    for row in frontier:
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(row.set_names, row.counts)
        )
        print(
            f"  {package} | topology={row.topology_signature} weapon_shape={row.weapon_shape} "
            f"weapon_damage={row.weapon_damage:.3f} max_magicka={row.max_magicka:.3f} "
            f"max_stamina={row.max_stamina:.3f} higher_resource_delta={row.higher_resource:.3f}"
        )
    print()

    print("UNRESOLVED PHYSICAL STATES")
    print(f"unresolved_physical_state_count={len(unresolved_realized)}")
    for row in sorted(
        unresolved_realized,
        key=lambda item: (-item.weapon_damage, -item.higher_resource, item.signature),
    )[:25]:
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(row.set_names, row.counts)
        )
        print(
            f"  {package} | reviewed_weapon_damage={row.weapon_damage:.3f} "
            f"reviewed_higher_resource_delta={row.higher_resource:.3f}"
        )
        for message in row.unresolved[:3]:
            print(f"    unresolved: {message}")
        if len(row.unresolved) > 3:
            print(f"    ... {len(row.unresolved) - 3} additional unresolved messages")
    if len(unresolved_realized) > 25:
        print(f"  ... {len(unresolved_realized) - 25} additional unresolved physical states omitted")
    print()

    physical_reduction_ready = bool(frontier) and not eligibility.unresolved
    print("PROOF STATUS")
    print(f"joint_named_gear_physical_reduction_ready={physical_reduction_ready}")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=compose each mechanic-complete physical gear Pareto state with the exact non-gear "
        "Weapon Damage subtotal and its same-build Max Magicka/Stamina base, then evaluate pure "
        "Sorcerer Font of Power at that actual higher-resource breakpoint; unresolved physical states "
        "remain proof blockers until their power mechanics are reviewed"
    )
    return 0 if physical_reduction_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
