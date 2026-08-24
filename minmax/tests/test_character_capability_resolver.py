from minmax.character_build.bar import Bar
from minmax.character_build.capability_resolver import CharacterCapabilityResolver
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _bar() -> Bar:
    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )

    return Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=slots,
    )


def _build_with_effect(effect: EffectVariant) -> CharacterBuild:
    armor = ArmorPiece(
        slot=GearSlot.HEAD,
        category=GearPieceCategory.NORMAL,
        effects=(effect,),
    )

    return CharacterBuild(
        name="Capability Test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(armor,),
        front_bar=_bar(),
    )


def test_resolver_returns_support_effect_registry():
    build = _build_with_effect(
        EffectVariant(
            name="major_courage",
            layer=EffectLayer.SLOTTED,
            source="Test Skill",
            magnitude=430,
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        )
    )

    registry = CharacterCapabilityResolver().resolve(
        build,
        BarId.FRONT,
    )

    effects = registry.all()

    assert len(effects) == 1
    assert effects[0].name == "major_courage"


def test_resolver_preserves_capability_metadata():
    build = _build_with_effect(
        EffectVariant(
            name="major_slayer",
            layer=EffectLayer.PROC,
            source="Master Architect",
            magnitude=10,
            duration=None,
            target_count=5,
            range=28,
            scaling="1 second per 10 Ultimate spent",
            trigger="ultimate_cast",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        )
    )

    registry = CharacterCapabilityResolver().resolve(
        build,
        BarId.FRONT,
    )

    effect = registry.all()[0]

    assert effect.name == "major_slayer"
    assert effect.source == "Master Architect"
    assert effect.magnitude == 10
    assert effect.target_count == 5
    assert effect.range == 28
    assert effect.scaling == "1 second per 10 Ultimate spent"
    assert effect.trigger is not None
    assert effect.trigger.trigger == "ultimate_cast"
    assert effect.target_type == SupportTargetType.GROUP


def test_resolver_preserves_self_and_group_as_distinct_capabilities():
    build = CharacterBuild(
        name="Capability Test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            ArmorPiece(
                slot=GearSlot.HEAD,
                effects=(
                    EffectVariant(
                        name="personal_stat",
                        layer=EffectLayer.PASSIVE,
                        source="Personal Passive",
                        target_type=SupportTargetType.SELF,
                    ),
                ),
            ),
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(
                    EffectVariant(
                        name="group_support",
                        layer=EffectLayer.PASSIVE,
                        source="Group Passive",
                        target_type=SupportTargetType.GROUP,
                    ),
                ),
            ),
        ),
        front_bar=_bar(),
    )

    registry = CharacterCapabilityResolver().resolve(
        build,
        BarId.FRONT,
    )

    effects = registry.all()

    assert {effect.name for effect in effects} == {
        "personal_stat",
        "group_support",
    }

    by_name = {effect.name: effect for effect in effects}

    assert by_name["personal_stat"].target_type == SupportTargetType.SELF
    assert by_name["group_support"].target_type == SupportTargetType.GROUP
    