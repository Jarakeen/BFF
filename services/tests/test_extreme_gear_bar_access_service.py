from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_gear_bar_access_service import ExtremeGearBarAccessService
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _ordinary(*, weapon_set: int, weapon_name: str):
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=(10, weapon_set),
        set_names=("Shared Five", weapon_name),
        counts=(5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Shoulders", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Chest", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Hands", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Waist", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Main Hand", weapon_set, weapon_name, "Inferno Staff"),
        ),
    )


def _oakensoul(*, weapon_set: int, weapon_name: str):
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2+1|unused:4",
        set_ids=(10, weapon_set, 99),
        set_names=("Shared Five", weapon_name, "Oakensoul Ring"),
        counts=(5, 2, 1),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Shoulders", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Chest", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Hands", 10, "Shared Five"),
            ExtremeNamedGearSlotAssignment("Ring1", 99, "Oakensoul Ring"),
            ExtremeNamedGearSlotAssignment("Main Hand", weapon_set, weapon_name, "Inferno Staff"),
        ),
    )


def test_ordinary_state_keeps_both_bars_activatable():
    front = _ordinary(weapon_set=20, weapon_name="Front Weapon")
    back = _ordinary(weapon_set=30, weapon_name="Back Weapon")

    access = ExtremeGearBarAccessService.resolve(ExtremeDualBarGearState(front=front, back=back))

    assert access.activatable_bars == ("front", "back")
    assert access.can_swap is True
    assert access.unresolved == ()


def test_oakensoul_state_preserves_backup_equipment_but_locks_activation_to_front():
    front = _oakensoul(weapon_set=20, weapon_name="Front Weapon")
    back = _oakensoul(weapon_set=30, weapon_name="Back Weapon")

    state = ExtremeDualBarGearState(front=front, back=back)
    access = ExtremeGearBarAccessService.resolve(state)

    assert state.back.weapon_assignments
    assert access.activatable_bars == ("front",)
    assert access.can_swap is False
    assert access.allows("front") is True
    assert access.allows("back") is False
    assert "Oakensoul Ring" in access.source_rule


def test_catalog_never_exposes_oakensoul_as_back_bar_active_snapshot():
    front = _oakensoul(weapon_set=20, weapon_name="Front Weapon")
    back = _oakensoul(weapon_set=30, weapon_name="Back Weapon")

    catalog = ExtremeDualBarGearStateCatalogService.build(
        (front, back),
        source_denominator_proven=True,
    )

    assert catalog.denominator_proven is True
    assert set(catalog.admissible_realizations(active_bar="front")) == {front, back}
    assert catalog.admissible_realizations(active_bar="back") == ()


def test_front_back_oakensoul_disagreement_fails_closed():
    front = _oakensoul(weapon_set=20, weapon_name="Front Weapon")
    back = _ordinary(weapon_set=30, weapon_name="Back Weapon")

    access = ExtremeGearBarAccessService.resolve(ExtremeDualBarGearState(front=front, back=back))

    assert access.activatable_bars == ()
    assert access.can_swap is False
    assert "disagrees" in access.unresolved[0]
