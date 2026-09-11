from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _shared_body():
    return (
        ExtremeNamedGearSlotAssignment("Head", 10, "Body A"),
        ExtremeNamedGearSlotAssignment("Shoulders", 10, "Body A"),
        ExtremeNamedGearSlotAssignment("Chest", 10, "Body A"),
        ExtremeNamedGearSlotAssignment("Hands", 10, "Body A"),
        ExtremeNamedGearSlotAssignment("Waist", 10, "Body A"),
        ExtremeNamedGearSlotAssignment("Legs", 20, "Body B"),
        ExtremeNamedGearSlotAssignment("Feet", 20, "Body B"),
        ExtremeNamedGearSlotAssignment("Necklace", 20, "Body B"),
        ExtremeNamedGearSlotAssignment("Ring1", 20, "Body B"),
        ExtremeNamedGearSlotAssignment("Ring2", 20, "Body B"),
    )


def _front():
    return ExtremeNamedGearSetRealization(
        topology_signature="5+5+2|unused:0",
        set_ids=(10, 20, 30),
        set_names=("Body A", "Body B", "Front Arena"),
        counts=(5, 5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            *_shared_body(),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", 30, "Front Arena", "Inferno Staff"
            ),
        ),
    )


def _back():
    return ExtremeNamedGearSetRealization(
        topology_signature="5+5+2|unused:0",
        set_ids=(10, 20, 40),
        set_names=("Body A", "Body B", "Back Arena"),
        counts=(5, 5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            *_shared_body(),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", 40, "Back Arena", "Restoration Staff"
            ),
        ),
    )


def test_dual_bar_state_materializes_shared_gear_and_distinct_weapon_bars():
    state = ExtremeDualBarGearState(front=_front(), back=_back())

    result = ExtremeDualBarGearStateService.materialize(PlayerBuild(), state)

    assert result.Armor["Head"]["Set"] == "Body A"
    assert result.Ring2.Set == "Body B"
    assert result.FrontBarWeapon.Set == "Front Arena"
    assert result.FrontBarWeapon.WeaponType == "Inferno Staff"
    assert result.BackBarWeapon.Set == "Back Arena"
    assert result.BackBarWeapon.WeaponType == "Restoration Staff"


def test_dual_bar_set_counts_use_canonical_active_bar_weapon_activation():
    state = ExtremeDualBarGearState(front=_front(), back=_back())

    front, back = ExtremeDualBarGearStateService.set_counts_by_bar(PlayerBuild(), state)

    assert dict(front) == {"Body A": 5, "Body B": 5, "Front Arena": 2}
    assert dict(back) == {"Body A": 5, "Body B": 5, "Back Arena": 2}


def test_dual_bar_state_rejects_conflicting_shared_body_jewelry():
    bad_back = ExtremeNamedGearSetRealization(
        topology_signature="5+5+2|unused:0",
        set_ids=(10, 20, 40),
        set_names=("Body A", "Body B", "Back Arena"),
        counts=(5, 5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 20, "Body B"),
            *_shared_body()[1:],
            ExtremeNamedGearSlotAssignment(
                "Main Hand", 40, "Back Arena", "Restoration Staff"
            ),
        ),
    )
    state = ExtremeDualBarGearState(front=_front(), back=bad_back)

    unresolved = ExtremeDualBarGearStateService.validate(state)

    assert unresolved == (
        "Front/back Extreme named-gear witnesses disagree on shared body/jewelry assignments",
    )

    try:
        ExtremeDualBarGearStateService.materialize(PlayerBuild(), state)
    except ValueError as exc:
        assert "disagree on shared body/jewelry" in str(exc)
    else:
        raise AssertionError("expected conflicting shared gear to fail closed")
