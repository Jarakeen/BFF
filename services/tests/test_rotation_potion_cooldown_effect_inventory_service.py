from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.passive_grant import PassiveGrant
from minmax.role import Role
from services.rotation_potion_cooldown_effect_inventory_service import (
    RotationPotionCooldownEffectInventoryService,
)


def _build(**overrides) -> CharacterBuild:
    values = dict(
        name="Potion inventory",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
    )
    values.update(overrides)
    return CharacterBuild(**values)


def _reduction(
    source: str,
    seconds: float = 2.0,
    *,
    layer: EffectLayer = EffectLayer.PASSIVE,
    **kwargs,
) -> EffectVariant:
    return EffectVariant(
        name="potion_cooldown_reduction",
        layer=layer,
        source=source,
        magnitude=seconds,
        **kwargs,
    )


def test_unconditional_build_effect_is_inventory_safe_when_scenario_inventory_is_complete() -> None:
    build = _build(
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(_reduction("Verified static set", layer=EffectLayer.PASSIVE),),
            ),
        ),
    )

    result = RotationPotionCooldownEffectInventoryService().resolve(
        character_build=build,
        scenario_inventory_complete=True,
    )

    assert result.complete
    assert tuple(effect.source for effect in result.effects) == ("Verified static set",)
    assert result.unresolved == ()


def test_dynamic_proc_is_retained_as_unresolved_topology_not_static_reduction() -> None:
    build = _build(
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(_reduction("Triggered set", layer=EffectLayer.PROC),),
            ),
        ),
    )

    result = RotationPotionCooldownEffectInventoryService().resolve(
        character_build=build,
        scenario_inventory_complete=True,
    )

    assert not result.complete
    assert result.effects == ()
    assert "dynamic layer=proc" in result.unresolved[0]


def test_active_bar_dependent_passive_cannot_be_flattened_into_global_cadence() -> None:
    grant = PassiveGrant(
        skill_line_id="green_balance",
        effect=_reduction("Bar represented passive"),
        requires_active_bar_representation=True,
    )

    result = RotationPotionCooldownEffectInventoryService().resolve(
        character_build=_build(),
        passives=(grant,),
        scenario_inventory_complete=True,
    )

    assert not result.complete
    assert result.effects == ()
    assert "active-bar skill-line representation" in result.unresolved[0]


def test_external_scenario_completeness_must_be_proven_even_when_build_has_no_modifier() -> None:
    service = RotationPotionCooldownEffectInventoryService()

    partial = service.resolve(character_build=_build())
    complete = service.resolve(
        character_build=_build(),
        scenario_inventory_complete=True,
    )

    assert not partial.complete
    assert partial.effects == ()
    assert partial.unresolved == (
        "external scenario potion cooldown effect inventory is not proven complete",
    )
    assert complete.complete
    assert complete.unresolved == ()
