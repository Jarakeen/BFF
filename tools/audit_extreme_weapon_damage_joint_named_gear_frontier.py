from __future__ import annotations

"""Expose named-set breakpoints that jointly matter to Weapon Damage and Sorcerer resource coupling.

This is a reduction diagnostic, not a final whole-build scorer. It reuses the canonical
named-set breakpoint and objective-relevance services for three objectives at the same
piece-count state: weapon_damage, max_magicka, and max_stamina. Mechanic-complete rows
are reduced to a Pareto frontier so later exact topology/slot realization only needs to
consider breakpoints that are not strictly worse on all three reviewed dimensions.

Unresolved rows are never pruned. A zero reviewed delta on an unresolved row is not proof
of zero mechanical value.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVES = ("weapon_damage", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class _JointBreakpoint:
    set_id: int
    set_name: str
    piece_count: int
    weapon_damage: float
    max_magicka: float
    max_stamina: float
    statuses: tuple[str, str, str]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved and all(status != "unresolved" for status in self.statuses)

    @property
    def has_positive_joint_value(self) -> bool:
        return self.weapon_damage > 0.0 or self.max_magicka > 0.0 or self.max_stamina > 0.0


def _status_value(row) -> str:
    return str(getattr(row.status, "value", row.status))


def _catalogs(repository: GearSetRepository, breakpoints):
    return {
        objective: ExtremeGearSetObjectiveRelevanceService(repository).build(
            objective,
            breakpoints,
        )
        for objective in OBJECTIVES
    }


def _row_map(catalog):
    return {
        (int(row.set_id), int(row.piece_count)): row
        for row in catalog.evidence
    }


def _joint_rows(repository: GearSetRepository):
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    catalogs = _catalogs(repository, breakpoints)
    maps = {objective: _row_map(catalog) for objective, catalog in catalogs.items()}

    keys = sorted(
        set().union(*(set(mapping) for mapping in maps.values())),
        key=lambda pair: (pair[0], pair[1]),
    )
    rows: list[_JointBreakpoint] = []
    for key in keys:
        evidence = [maps[objective].get(key) for objective in OBJECTIVES]
        present = next((row for row in evidence if row is not None), None)
        if present is None:
            continue

        deltas: list[float] = []
        statuses: list[str] = []
        unresolved: list[str] = []
        for objective, row in zip(OBJECTIVES, evidence):
            if row is None:
                deltas.append(0.0)
                statuses.append("missing")
                unresolved.append(
                    f"{present.set_name} {present.piece_count}pc: no {objective} relevance evidence"
                )
                continue
            deltas.append(float(row.reviewed_delta))
            statuses.append(_status_value(row))
            unresolved.extend(tuple(row.candidate.unresolved or ()))
            if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED:
                unresolved.append(
                    f"{row.set_name} {row.piece_count}pc: {objective} relevance unresolved"
                )

        rows.append(
            _JointBreakpoint(
                set_id=int(present.set_id),
                set_name=str(present.set_name),
                piece_count=int(present.piece_count),
                weapon_damage=deltas[0],
                max_magicka=deltas[1],
                max_stamina=deltas[2],
                statuses=tuple(statuses),
                unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
            )
        )

    return breakpoints, catalogs, tuple(rows)


def _dominates(left: _JointBreakpoint, right: _JointBreakpoint) -> bool:
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


def _pareto(rows: tuple[_JointBreakpoint, ...]) -> tuple[_JointBreakpoint, ...]:
    complete = tuple(row for row in rows if row.mechanic_complete and row.has_positive_joint_value)
    frontier = tuple(
        row
        for row in complete
        if not any(other is not row and _dominates(other, row) for other in complete)
    )
    return tuple(
        sorted(
            frontier,
            key=lambda row: (
                -row.weapon_damage,
                -max(row.max_magicka, row.max_stamina),
                -row.max_magicka,
                -row.max_stamina,
                row.piece_count,
                row.set_name.casefold(),
                row.set_id,
            ),
        )
    )


def main() -> int:
    repository = GearSetRepository(DATABASE)
    breakpoints, catalogs, rows = _joint_rows(repository)
    frontier = _pareto(rows)
    unresolved_rows = tuple(row for row in rows if row.unresolved)

    print("EXTREME WEAPON DAMAGE + MAX RESOURCE NAMED-GEAR BREAKPOINT FRONTIER")
    print(f"database={DATABASE}")
    print("objectives=('weapon_damage', 'max_magicka', 'max_stamina')")
    print("scope=canonical named-set bonus breakpoints only")
    print("physical_slot_realization_in_scope=False")
    print("whole_build_same_resource_proof=False")
    print()

    print("DENOMINATOR")
    print(f"breakpoint_sets={len(breakpoints.sets)}")
    print(f"joint_breakpoints_reviewed={len(rows)}")
    for objective in OBJECTIVES:
        catalog = catalogs[objective]
        print(
            f"{objective}_relevance_rows={len(catalog.evidence)} "
            f"relevant={len(catalog.relevant)} unresolved={len(catalog.unresolved_evidence)}"
        )
    print()

    print("MECHANIC-COMPLETE PARETO BREAKPOINTS")
    print(f"pareto_count={len(frontier)}")
    for row in frontier:
        higher_resource = max(row.max_magicka, row.max_stamina)
        print(
            f"  {row.set_name} {row.piece_count}pc | "
            f"weapon_damage={row.weapon_damage:.3f} "
            f"max_magicka={row.max_magicka:.3f} "
            f"max_stamina={row.max_stamina:.3f} "
            f"higher_resource_delta={higher_resource:.3f}"
        )
    print()

    print("UNRESOLVED JOINT BREAKPOINTS RETAINED")
    print(f"unresolved_joint_breakpoint_count={len(unresolved_rows)}")
    for row in unresolved_rows[:50]:
        print(
            f"  {row.set_name} {row.piece_count}pc | statuses={row.statuses!r} "
            f"reviewed=({row.weapon_damage:.3f}, {row.max_magicka:.3f}, {row.max_stamina:.3f})"
        )
        for message in row.unresolved:
            print(f"    unresolved: {message}")
    if len(unresolved_rows) > 50:
        print(f"  ... {len(unresolved_rows) - 50} additional unresolved rows omitted from display")
    print()

    print("PROOF STATUS")
    print("joint_named_gear_breakpoint_reduction_ready=True")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=realize legal named-set topologies from the Pareto plus unresolved breakpoint pool, "
        "then score each same equipped state for Weapon Damage and higher Max Resource so Sorcerer "
        "Font of Power is evaluated on the actual candidate rather than an independent resource maximum"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
