from __future__ import annotations

"""Triage unresolved named-set Weapon Damage mechanics at the semantic breakpoint layer.

This audit does not realize thousands of physical gear combinations. It takes the
retained unresolved joint breakpoints, applies the existing proof-safe Weapon Damage
upper-bound service once per semantic breakpoint, and separates rows with finite flat
or percentage ceilings from rows whose formula still has no finite reviewed bound.

The corrected resolved same-build incumbent (9,451.238 Weapon Damage) is carried only
as the current hurdle. This audit does not claim that a single breakpoint ceiling can
be added directly to that incumbent or that an unresolved set is physically legal with
its strongest possible partner. Those composition questions belong to the next reduced
realization pass after semantic blockers are collapsed.
"""

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_power_upper_bound_service import (
    ExtremeGearSetPowerUpperBoundService,
)
from tools.audit_extreme_weapon_damage_joint_named_gear_frontier import _joint_rows

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
RESOLVED_INCUMBENT = 9451.238


def _category(message: str) -> str:
    text = str(message or "").casefold()
    if "ultimate" in text:
        return "ultimate_consumed_formula"
    if "minor buff" in text:
        return "per_minor_buff_formula"
    if "weapon-trait" in text or "weapon trait" in text:
        return "weapon_trait_amplification"
    if "second-mundus" in text or "second mundus" in text:
        return "second_mundus"
    if "numeric ceiling" in text:
        return "no_finite_numeric_ceiling"
    return "other"


def main() -> int:
    repository = GearSetRepository(DATABASE)
    breakpoints, catalogs, rows = _joint_rows(repository)
    weapon_map = {
        (int(row.set_id), int(row.piece_count)): row
        for row in catalogs[OBJECTIVE].evidence
    }
    unresolved_rows = tuple(row for row in rows if row.unresolved)

    finite_flat = []
    finite_percent = []
    unbounded = []
    categories = Counter()

    for joint in unresolved_rows:
        evidence = weapon_map.get((joint.set_id, joint.piece_count))
        if evidence is None:
            unbounded.append((joint, 0.0, 0.0, ("missing Weapon Damage relevance evidence",), (), ()))
            categories["missing_weapon_damage_evidence"] += 1
            continue

        flat = 0.0
        percent = 0.0
        assumptions = []
        blockers = []
        buffs = []
        for bonus in evidence.candidate.source_bonuses:
            bound = ExtremeGearSetPowerUpperBoundService.build(
                str(bonus.description or ""),
                OBJECTIVE,
            )
            flat += float(bound.flat_upper_bound)
            percent += float(bound.percent_upper_bound)
            assumptions.extend(bound.assumptions)
            blockers.extend(bound.unresolved)
            buffs.extend(bound.named_buffs)

        blockers = tuple(dict.fromkeys(str(item) for item in blockers if str(item)))
        assumptions = tuple(dict.fromkeys(str(item) for item in assumptions if str(item)))
        buffs = tuple(dict.fromkeys(str(item) for item in buffs if str(item)))

        if blockers:
            unbounded.append((joint, flat, percent, blockers, assumptions, buffs))
            for blocker in blockers:
                categories[_category(blocker)] += 1
        elif percent > 0.0:
            finite_percent.append((joint, flat, percent, assumptions, buffs))
        else:
            finite_flat.append((joint, flat, assumptions, buffs))

    finite_flat.sort(key=lambda item: (-item[1], item[0].set_name.casefold(), item[0].piece_count))
    finite_percent.sort(key=lambda item: (-item[2], -item[1], item[0].set_name.casefold(), item[0].piece_count))
    unbounded.sort(key=lambda item: (item[0].set_name.casefold(), item[0].piece_count))

    print("EXTREME WEAPON DAMAGE UNRESOLVED NAMED-GEAR SEMANTIC TRIAGE")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print(f"resolved_same_build_incumbent={RESOLVED_INCUMBENT:.3f}")
    print("scope=retained unresolved joint named-set breakpoints only")
    print("physical_realization_in_scope=False")
    print("same_build_composition_claimed=False")
    print()

    print("DENOMINATOR")
    print(f"breakpoint_sets={len(breakpoints.sets)}")
    print(f"unresolved_joint_breakpoints={len(unresolved_rows)}")
    print(f"finite_flat_bound_rows={len(finite_flat)}")
    print(f"finite_percent_bound_rows={len(finite_percent)}")
    print(f"still_unbounded_rows={len(unbounded)}")
    print()

    print("FINITE FLAT CEILINGS")
    for joint, flat, assumptions, buffs in finite_flat:
        print(f"  {joint.set_name} {joint.piece_count}pc | flat_upper_bound={flat:.3f}")
        if buffs:
            print(f"    named_buffs={buffs!r}")
        for assumption in assumptions:
            print(f"    assumption: {assumption}")
    print()

    print("FINITE PERCENT CEILINGS")
    for joint, flat, percent, assumptions, buffs in finite_percent:
        print(
            f"  {joint.set_name} {joint.piece_count}pc | flat_upper_bound={flat:.3f} "
            f"percent_upper_bound={percent:.6f}"
        )
        if buffs:
            print(f"    named_buffs={buffs!r}")
        for assumption in assumptions:
            print(f"    assumption: {assumption}")
    print()

    print("STILL UNBOUNDED SEMANTIC ROWS")
    for joint, flat, percent, blockers, assumptions, buffs in unbounded:
        print(
            f"  {joint.set_name} {joint.piece_count}pc | partial_flat_bound={flat:.3f} "
            f"partial_percent_bound={percent:.6f}"
        )
        if buffs:
            print(f"    named_buffs={buffs!r}")
        for assumption in assumptions:
            print(f"    assumption: {assumption}")
        for blocker in blockers:
            print(f"    unresolved: {blocker}")
    print()

    print("UNBOUNDED BLOCKER CATEGORIES")
    for name, count in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {name}={count}")
    print()

    print("PROOF STATUS")
    print(f"semantic_breakpoints_bounded={len(finite_flat) + len(finite_percent)}")
    print(f"semantic_breakpoints_still_unbounded={len(unbounded)}")
    print("resolved_class_frontier_incumbent_ready=True")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=resolve the small still-unbounded semantic categories first, then feed every finite flat/percent ceiling into a reduced physical topology bound against the 9451.238 incumbent; do not enumerate the old 60k unresolved combinations individually"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
