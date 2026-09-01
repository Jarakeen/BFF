from minmax.character_build.bar import Bar
from minmax.character_build.capability_resolver import CharacterCapabilityResolver
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _build() -> CharacterBuild:
    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{index}",
            skill_line_id="restoration_staff",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )
    return CharacterBuild(
        name="Potion Capability Test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=slots,
        ),
    )


def _potion_effect(*, target=SupportTargetType.SELF, trigger="potion_use") -> EffectVariant:
    return EffectVariant(
        name="increase_spell_power",
        layer=EffectLayer.CONSUMABLE,
        source="Potion: canonical family",
        trigger=trigger,
        condition="selected potion available; activation and uptime are not assumed",
        target_type=target,
        category=SupportEffectCategory.BUFF,
    )


def test_self_potion_availability_is_preserved_as_triggered_capability():
    registry = CharacterCapabilityResolver().resolve(
        _build(),
        BarId.FRONT,
        consumable_effects=(_potion_effect(),),
    )

    effects = registry.all()
    assert len(effects) == 1
    effect = effects[0]
    assert effect.name == "increase_spell_power"
    assert effect.target_type is SupportTargetType.SELF
    assert effect.trigger is not None
    assert effect.trigger.trigger == "potion_use"
    assert effect.trigger.condition == "selected potion available; activation and uptime are not assumed"
    assert effect.duration is None
    assert effect.cooldown is None


def test_group_target_consumable_is_rejected_from_capability_boundary():
    registry = CharacterCapabilityResolver().resolve(
        _build(),
        BarId.FRONT,
        consumable_effects=(_potion_effect(target=SupportTargetType.GROUP),),
    )

    assert registry.all() == ()


def test_consumable_with_wrong_trigger_is_rejected_from_capability_boundary():
    registry = CharacterCapabilityResolver().resolve(
        _build(),
        BarId.FRONT,
        consumable_effects=(_potion_effect(trigger="standing"),),
    )

    assert registry.all() == ()
