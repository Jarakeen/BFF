from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_build_materializer_service import ExtremeNamedGearBuildMaterializerService
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)
from models.build_model import PlayerBuild


def _witness():
    return ExtremeNamedGearSetRealization(
        topology_signature="5+5+2|unused:0",
        set_ids=(10, 20, 30),
        set_names=("Five A", "Five B", "Arena Staff"),
        counts=(5, 5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Shoulders", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Chest", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Hands", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Waist", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Legs", 20, "Five B"),
            ExtremeNamedGearSlotAssignment("Feet", 20, "Five B"),
            ExtremeNamedGearSlotAssignment("Necklace", 20, "Five B"),
            ExtremeNamedGearSlotAssignment("Ring1", 20, "Five B"),
            ExtremeNamedGearSlotAssignment("Ring2", 20, "Five B"),
            ExtremeNamedGearSlotAssignment("Main Hand", 30, "Arena Staff", "Inferno Staff"),
        ),
    )


def test_materializer_writes_proven_body_jewelry_and_active_weapon_assignments():
    result = ExtremeNamedGearBuildMaterializerService.materialize(
        PlayerBuild(Name="Extreme"),
        _witness(),
        active_bar="front",
    )

    assert result.Armor["Head"]["Set"] == "Five A"
    assert result.Armor["Legs"]["Set"] == "Five B"
    assert result.Necklace.Set == "Five B"
    assert result.Ring1.Set == "Five B"
    assert result.FrontBarWeapon.Set == "Arena Staff"
    assert result.FrontBarWeapon.WeaponType == "Inferno Staff"
    assert result.FrontBarOffHand.is_empty


def test_materializer_places_weapon_only_on_selected_active_bar():
    build = PlayerBuild(Name="Extreme")
    build.FrontBarWeapon.Set = "Inactive Bar Set"
    build.FrontBarWeapon.WeaponType = "Restoration Staff"

    result = ExtremeNamedGearBuildMaterializerService.materialize(
        build,
        _witness(),
        active_bar="back",
    )

    assert result.BackBarWeapon.Set == "Arena Staff"
    assert result.BackBarWeapon.WeaponType == "Inferno Staff"
    assert result.FrontBarWeapon.Set == "Inactive Bar Set"


def test_materializer_rejects_unknown_bar_instead_of_guessing():
    try:
        ExtremeNamedGearBuildMaterializerService.materialize(
            PlayerBuild(), _witness(), active_bar="middle"
        )
    except ValueError as exc:
        assert "unsupported active bar" in str(exc)
    else:
        raise AssertionError("expected unsupported active bar to fail closed")
