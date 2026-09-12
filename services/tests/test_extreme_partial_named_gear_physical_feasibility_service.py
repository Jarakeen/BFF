from __future__ import annotations

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)
from services.service_catalog import canonical_service_for


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


def test_partial_named_gear_feasibility_is_registered_canonically() -> None:
    descriptor = canonical_service_for("partial_named_gear_physical_feasibility")

    assert descriptor is not None
    assert descriptor.service_id == "extreme.partial_named_gear_physical_feasibility"
    assert descriptor.implementation_path == (
        "services.extreme_partial_named_gear_physical_feasibility_service"
    )


def test_empty_prefix_is_optimistically_possible() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    result = service.evaluate(topology, ())

    assert result.possible is True
    assert result.selected_count == 0
    assert result.compatible_physical_shapes > 0


def test_impossible_selected_prefix_is_rejected_before_future_sets_exist() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(3, 2), unused_units=7)
    selected = (_rings_only(10),)

    result = service.evaluate(topology, selected)

    assert result.possible is False
    assert result.compatible_physical_shapes == 0
    assert "cannot fit any canonical physical realization" in result.reason


def test_impossible_prefix_has_no_legal_full_completion() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(3, 2), unused_units=7)
    selected = (_rings_only(10),)
    completion = (*selected, _broad(20))

    assert service.is_possible(topology, selected) is False
    assert ExtremeNamedGearSetRealizationService.find_witness(topology, completion) is None


def test_complete_prefix_matches_full_named_witness_legality() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)
    rows = (_broad(10), _broad(20), _broad(30))

    partial = service.evaluate(topology, rows)
    full = ExtremeNamedGearSetRealizationService.find_witness(topology, rows)

    assert partial.possible is True
    assert full is not None


def test_multiple_selected_mythics_fail_closed() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(1, 1), unused_units=10)
    rows = (_broad(10, category="Mythic"), _broad(20, category="Mythic"))

    result = service.evaluate(topology, rows)

    assert result.possible is False
    assert result.reason == "selected prefix violates global named-set legality"


def test_repeated_prefix_shape_reuses_cached_result() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    topology = ExtremeGearSetCountTopology(counts=(3, 2), unused_units=7)
    selected = (_rings_only(10),)

    first = service.evaluate(topology, selected)
    second = service.evaluate(topology, selected)

    assert first is second


def test_repeated_set_shape_is_interned_by_canonical_set_id() -> None:
    service = ExtremePartialNamedGearPhysicalFeasibilityService()
    first_row = _broad(10)
    equivalent_row = _broad(10)

    first = service._cached_shape(first_row)
    second = service._cached_shape(equivalent_row)

    assert first is second
    assert tuple(service._shape_cache) == (10,)
