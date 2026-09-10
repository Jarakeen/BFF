from __future__ import annotations

from services.extreme_gear_physical_slot_realization_service import (
    BODY_JEWELRY_SINGLE_SLOTS,
    ExtremeGearPhysicalSlotRealizationService,
    ExtremeWeaponSlotShape,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)


def _catalog(*topologies: ExtremeGearSetCountTopology, unresolved=()):
    return ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=tuple(topologies),
        unresolved=tuple(unresolved),
        physical_slot_realization_proven=False,
    )


def test_two_handed_weapon_contributes_two_units_to_same_set_only():
    topology = ExtremeGearSetCountTopology((5, 5, 2), 0)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(_catalog(topology))

    two_handed = [
        row for row in catalog.realizations
        if row.topology_signature == topology.signature
        and row.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED
    ]

    assert two_handed
    assert all(len(set(row.weapon_set_indices)) == 1 for row in two_handed)
    assert any(row.weapon_set_indices == (2, 2) for row in two_handed)
    assert all(row.body_jewelry_units <= BODY_JEWELRY_SINGLE_SLOTS for row in two_handed)


def test_paired_one_handed_weapon_can_split_two_one_piece_sets():
    topology = ExtremeGearSetCountTopology((5, 5, 1, 1), 0)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(_catalog(topology))

    split = [
        row for row in catalog.realizations
        if row.weapon_shape is ExtremeWeaponSlotShape.PAIRED_ONE_HANDED
        and row.weapon_set_indices == (2, 3)
    ]

    assert split
    assert split[0].body_jewelry_counts == (5, 5, 0, 0)
    assert split[0].body_jewelry_units == 10


def test_single_one_handed_shape_allows_eleven_used_set_units():
    topology = ExtremeGearSetCountTopology((5, 5, 1), 1)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(_catalog(topology))

    singles = [
        row for row in catalog.realizations
        if row.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE
    ]

    assert singles
    assert any(row.body_jewelry_units == 10 for row in singles)


def test_topology_at_or_below_ten_units_can_use_no_set_bearing_weapon():
    topology = ExtremeGearSetCountTopology((5, 5), 2)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(_catalog(topology))

    none_rows = [
        row for row in catalog.realizations
        if row.weapon_shape is ExtremeWeaponSlotShape.NONE
    ]

    assert none_rows
    assert none_rows[0].body_jewelry_counts == (5, 5)


def test_generic_shape_proof_does_not_claim_named_set_slot_eligibility():
    topology = ExtremeGearSetCountTopology((5, 5, 2), 0)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(_catalog(topology))

    assert catalog.generic_slot_shape_denominator_proven is True
    assert catalog.named_set_slot_eligibility_proven is False
    assert catalog.physical_slot_realization_proven is False


def test_upstream_unresolved_state_prevents_generic_shape_proof():
    topology = ExtremeGearSetCountTopology((5,), 7)
    catalog = ExtremeGearPhysicalSlotRealizationService().build(
        _catalog(topology, unresolved=("Gear set Mystery has unknown capacity",))
    )

    assert catalog.unresolved == ("Gear set Mystery has unknown capacity",)
    assert catalog.generic_slot_shape_denominator_proven is False
    assert catalog.physical_slot_realization_proven is False
