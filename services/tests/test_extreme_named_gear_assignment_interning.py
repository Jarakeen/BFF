from __future__ import annotations

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe",
    "Mace",
    "Sword",
    "Dagger",
    "Shield",
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


def _ordinary(set_id: int) -> tuple[
    ExtremeNamedGearSetSlotEligibility,
    ExtremeGearSetBonusBreakpoints,
]:
    return (
        ExtremeNamedGearSetSlotEligibility(
            set_id=set_id,
            name=f"Set {set_id}",
            category="Trial",
            max_equip_count=5,
            armor_slots=_BODY,
            jewelry_slots=("Necklace", "Ring"),
            weapon_types=_WEAPONS,
        ),
        ExtremeGearSetBonusBreakpoints(
            set_id=set_id,
            name=f"Set {set_id}",
            max_equip_count=5,
            bonus_counts=(2,),
        ),
    )


def test_repeated_set_slot_assignments_are_interned_across_named_combinations() -> None:
    rows = tuple(_ordinary(set_id) for set_id in (10, 20, 30))
    service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(row[1] for row in rows),
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=tuple(row[0] for row in rows),
        ),
    )

    result = service.realize_topology(
        ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    )

    assert result.assignments_considered == 3
    assert result.assignments_realized == 3

    by_ids = {row.set_ids: row for row in result.realizations}
    first = by_ids[(10, 20)]
    second = by_ids[(10, 30)]

    first_set_10 = {
        (row.slot, row.weapon_type): row
        for row in first.assignments
        if row.set_id == 10
    }
    second_set_10 = {
        (row.slot, row.weapon_type): row
        for row in second.assignments
        if row.set_id == 10
    }

    assert first_set_10.keys() == second_set_10.keys()
    assert first_set_10
    assert all(
        first_set_10[key] is second_set_10[key]
        for key in first_set_10
    )
