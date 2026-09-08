from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.role import Role
from services.rotation_build_potion_cooldown_service import (
    RotationBuildPotionCooldownService,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemEvidence,
)


def _build(*effects: EffectVariant) -> CharacterBuild:
    armor = (
        ArmorPiece(slot=GearSlot.CHEST, effects=tuple(effects)),
    ) if effects else ()
    return CharacterBuild(
        name="Potion cooldown build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=armor,
        potion_id="test_potion",
    )


def _reduction(source: str, seconds: float, layer: EffectLayer = EffectLayer.PASSIVE) -> EffectVariant:
    return EffectVariant(
        name="potion_cooldown_reduction",
        layer=layer,
        source=source,
        magnitude=seconds,
    )


def test_complete_inventory_promotes_build_effect_to_effective_cooldown() -> None:
    result = RotationBuildPotionCooldownService().resolve(
        character_build=_build(_reduction("Static passive", 2.0)),
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(),
        scenario_inventory_complete=True,
    )

    assert result.inventory.complete
    assert result.effect_evidence.total_reduction_seconds == 2.0
    assert result.effective.complete
    assert result.effective.effective_cooldown_seconds == 43.0


def test_unknown_scenario_inventory_keeps_effective_cooldown_partial() -> None:
    result = RotationBuildPotionCooldownService().resolve(
        character_build=_build(_reduction("Static passive", 2.0)),
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(),
    )

    assert not result.inventory.complete
    assert result.effective.effective_cooldown_seconds is None
    assert any("scenario" in item for item in result.effective.unresolved)
    assert any("not proven complete" in item for item in result.effective.unresolved)


def test_dynamic_build_modifier_is_not_flattened_into_effective_cadence() -> None:
    result = RotationBuildPotionCooldownService().resolve(
        character_build=_build(_reduction("Triggered set", 3.0, EffectLayer.PROC)),
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(),
        scenario_inventory_complete=True,
    )

    assert result.effect_evidence.reductions == ()
    assert result.effective.effective_cooldown_seconds is None
    assert any("dynamic layer=proc" in item for item in result.effective.unresolved)


def test_verified_base_override_is_preserved_through_composition() -> None:
    result = RotationBuildPotionCooldownService().resolve(
        character_build=_build(),
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(),
        scenario_inventory_complete=True,
        base_cooldown_seconds=40.0,
    )

    assert result.effective.complete
    assert result.effective.effective_cooldown_seconds == 40.0
