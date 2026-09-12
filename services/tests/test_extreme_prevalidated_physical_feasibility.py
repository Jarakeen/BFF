from __future__ import annotations

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
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


def _broad(set_id: int, *, category: str = "Trial") -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category=category,
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _rings_only(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Rings {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=(),
        jewelry_slots=("Ring",),
        weapon_types=(),
    )


def test_prevalidated_path_matches_public_api_for_valid_exact_search_prefixes() -> None:
    topology = ExtremeGearSetCountTopology(counts=(5, 3, 2, 1, 1), unused_units=0)

    prefixes = (
        (_broad(10),),
        (_broad(10), _broad(20)),
        (_broad(10), _broad(20), _rings_only(30)),
        (_broad(10), _broad(20), _rings_only(30), _broad(40, category="Mythic")),
    )

    for prefix in prefixes:
        public_service = ExtremePartialNamedGearPhysicalFeasibilityService()
        fast_service = ExtremePartialNamedGearPhysicalFeasibilityService()

        public = public_service.evaluate(topology, prefix)
        fast = fast_service._evaluate_prevalidated(topology, prefix)

        assert fast == public
        assert fast_service._is_possible_prevalidated(topology, prefix) is public.possible


def test_child_compatible_physicals_match_full_universe_and_parent_filter() -> None:
    topology = ExtremeGearSetCountTopology(counts=(5, 3, 2, 1, 1), unused_units=0)
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    parent = (_broad(10), _broad(20))
    child = (*parent, _rings_only(30))

    parent_physicals = service._compatible_physicals_prevalidated(topology, parent)

    # Use a fresh service for the full-universe reference so no cached child result
    # can make this equality tautological.
    reference_service = ExtremePartialNamedGearPhysicalFeasibilityService()
    from_full_universe = reference_service._compatible_physicals_prevalidated(topology, child)
    from_parent_frontier = service._compatible_physicals_prevalidated(
        topology,
        child,
        candidates=parent_physicals,
    )

    assert from_parent_frontier == from_full_universe
    assert set(from_parent_frontier).issubset(set(parent_physicals))


def test_public_api_still_rejects_contract_violations_before_fast_path() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(5, 3), unused_units=4)
    repeated = (_broad(10), _broad(10))

    result = service.evaluate(topology, repeated)

    assert result.possible is False
    assert result.reason == "selected prefix repeats a named set identity"
