from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _realization(*, shared_set: int, weapon_set: int, weapon_type: str):
    shared_name = f"Shared {shared_set}"
    weapon_name = f"Weapon {weapon_set}"
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=(shared_set, weapon_set),
        set_names=(shared_name, weapon_name),
        counts=(5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Shoulders", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Chest", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Hands", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Waist", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", weapon_set, weapon_name, weapon_type
            ),
        ),
    )


def test_catalog_pairs_only_snapshots_with_identical_shared_body_jewelry():
    front = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")
    back = _realization(shared_set=10, weapon_set=30, weapon_type="Restoration Staff")
    incompatible = _realization(shared_set=11, weapon_set=40, weapon_type="Ice Staff")

    catalog = ExtremeDualBarGearStateCatalogService.build(
        (front, back, incompatible),
        source_denominator_proven=True,
    )

    assert catalog.denominator_proven is True
    assert catalog.active_snapshots_reviewed == 3
    # Two compatible snapshots form four ordered front/back states; the lone
    # incompatible shared layout can still legally pair with itself.
    assert catalog.compatible_pairs_reviewed == 5
    assert len(catalog.states) == 5
    assert any(state.front == front and state.back == back for state in catalog.states)
    assert not any(
        state.front == front and state.back == incompatible for state in catalog.states
    )


def test_every_admissible_snapshot_has_at_least_one_complete_two_bar_witness():
    first = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")
    second = _realization(shared_set=10, weapon_set=30, weapon_type="Restoration Staff")

    catalog = ExtremeDualBarGearStateCatalogService.build(
        (first, second),
        source_denominator_proven=True,
    )

    front = catalog.admissible_realizations(active_bar="front")
    back = catalog.admissible_realizations(active_bar="back")
    assert set(front) == {first, second}
    assert set(back) == {first, second}


def test_source_gap_or_unresolved_pair_boundary_keeps_denominator_open():
    row = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")

    source_gap = ExtremeDualBarGearStateCatalogService.build(
        (row,),
        source_denominator_proven=False,
    )
    unresolved = ExtremeDualBarGearStateCatalogService.build(
        (row,),
        source_denominator_proven=True,
        unresolved=("named gear source truncated",),
    )

    assert source_gap.denominator_proven is False
    assert unresolved.denominator_proven is False
    assert unresolved.unresolved == ("named gear source truncated",)


def test_invalid_active_bar_fails_closed():
    row = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")
    catalog = ExtremeDualBarGearStateCatalogService.build(
        (row,), source_denominator_proven=True
    )

    try:
        catalog.admissible_realizations(active_bar="middle")
    except ValueError as exc:
        assert "unsupported active bar" in str(exc)
    else:
        raise AssertionError("expected unsupported active bar to fail closed")
