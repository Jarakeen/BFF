from __future__ import annotations

from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


def _ordinary(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"),
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=(
            "Axe", "Mace", "Sword", "Dagger", "Shield",
            "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
            "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
        ),
    )


def _monster() -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=30,
        name="Monster",
        category="Monster Set",
        max_equip_count=2,
        armor_slots=("Head", "Shoulders"),
    )


def _mythic_ring(set_id: int = 40, name: str = "Mythic Ring") -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Mythic",
        max_equip_count=1,
        jewelry_slots=("Ring",),
    )


def _arena_staff() -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=50,
        name="Arena Staff",
        category="Arena",
        max_equip_count=2,
        weapon_types=("Inferno Staff",),
    )


def test_five_five_two_named_sets_receive_concrete_legal_witness():
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    witness = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_ordinary(10, "Five A"), _ordinary(20, "Five B"), _monster()),
    )

    assert witness is not None
    assert witness.topology_signature == "5+5+2|unused:0"
    assert witness.set_ids == (10, 20, 30)
    assert len(witness.assignments) in {11, 12}
    assert {row.slot for row in witness.body_jewelry_assignments}.issubset(
        {"Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet", "Necklace", "Ring1", "Ring2"}
    )
    monster_slots = {
        row.slot for row in witness.body_jewelry_assignments if row.set_id == 30
    }
    assert monster_slots == {"Head", "Shoulders"}


def test_mythic_ring_is_forced_to_one_of_the_two_physical_ring_slots():
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 1), unused_units=1)

    witness = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_ordinary(10, "Five A"), _ordinary(20, "Five B"), _mythic_ring()),
    )

    assert witness is not None
    mythic = next(row for row in witness.assignments if row.set_id == 40)
    assert mythic.slot in {"Ring1", "Ring2"}
    assert mythic.weapon_type == ""


def test_two_distinct_mythics_cannot_be_equipped_together():
    topology = ExtremeGearSetCountTopology(counts=(1, 1), unused_units=10)

    assert ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_mythic_ring(40, "Mythic One"), _mythic_ring(41, "Mythic Two")),
    ) is None


def test_zero_count_mythic_does_not_block_one_equipped_mythic():
    topology = ExtremeGearSetCountTopology(counts=(1, 0), unused_units=11)

    witness = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_mythic_ring(40, "Equipped Mythic"), _mythic_ring(41, "Unequipped Mythic")),
    )

    assert witness is not None
    assert {row.set_id for row in witness.assignments} == {40}


def test_mythic_category_matching_is_case_and_whitespace_insensitive():
    topology = ExtremeGearSetCountTopology(counts=(1, 1), unused_units=10)
    first = _mythic_ring(40, "Mythic One")
    second = ExtremeNamedGearSetSlotEligibility(
        set_id=41,
        name="Mythic Two",
        category="  MYTHIC  ",
        max_equip_count=1,
        jewelry_slots=("Ring",),
    )

    assert ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (first, second),
    ) is None


def test_arena_staff_requires_two_handed_weapon_shape_and_exact_weapon_type():
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)

    witness = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_ordinary(10, "Five A"), _ordinary(20, "Five B"), _arena_staff()),
    )

    assert witness is not None
    assert witness.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED
    weapon = next(row for row in witness.weapon_assignments if row.set_id == 50)
    assert weapon.slot == "Main Hand"
    assert weapon.weapon_type == "Inferno Staff"


def test_duplicate_set_identity_cannot_satisfy_two_topology_parts():
    topology = ExtremeGearSetCountTopology(counts=(5, 5), unused_units=2)
    repeated = _ordinary(10, "Same Set")

    assert ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (repeated, repeated),
    ) is None


def test_set_count_above_canonical_capacity_is_rejected():
    topology = ExtremeGearSetCountTopology(counts=(3,), unused_units=9)

    assert ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (_monster(),),
    ) is None


def test_two_monster_like_sets_cannot_both_claim_same_head_shoulders_pair():
    topology = ExtremeGearSetCountTopology(counts=(2, 2), unused_units=8)
    first = _monster()
    second = ExtremeNamedGearSetSlotEligibility(
        set_id=31,
        name="Monster Two",
        category="Monster Set",
        max_equip_count=2,
        armor_slots=("Head", "Shoulders"),
    )

    assert ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        (first, second),
    ) is None


def test_paired_one_handed_shape_can_split_weapon_set_units_between_named_sets():
    topology = ExtremeGearSetCountTopology(counts=(1, 1), unused_units=10)
    main = ExtremeNamedGearSetSlotEligibility(
        set_id=60,
        name="Main Only",
        category="Arena",
        max_equip_count=1,
        weapon_types=("Sword",),
    )
    off = ExtremeNamedGearSetSlotEligibility(
        set_id=61,
        name="Off Only",
        category="Arena",
        max_equip_count=1,
        weapon_types=("Shield",),
    )

    witness = ExtremeNamedGearSetRealizationService.find_witness(topology, (main, off))

    assert witness is not None
    assert witness.weapon_shape is ExtremeWeaponSlotShape.PAIRED_ONE_HANDED
    assert [(row.slot, row.weapon_type) for row in witness.weapon_assignments] == [
        ("Main Hand", "Sword"),
        ("Off Hand", "Shield"),
    ]
