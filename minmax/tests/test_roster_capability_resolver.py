from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.roster_capability_resolver import RosterCapabilityResolver
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


def _character(
    name: str,
    role: Role,
    effect: EffectVariant,
) -> CharacterBuild:
    return CharacterBuild(
        name=name,
        character_class=CharacterClass.WARDEN,
        role=role,
        armor=(
            ArmorPiece(
                slot=GearSlot.HEAD,
                effects=(effect,),
            ),
        ),
        front_bar=_bar(),
    )


def test_roster_indexes_character_capability_by_effect_name():
    character = _character(
        "Healer One",
        Role.HEALER,
        EffectVariant(
            name="major_courage",
            layer=EffectLayer.SLOTTED,
            source="Test Skill",
            magnitude=430,
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        ),
    )

    capabilities = RosterCapabilityResolver().resolve(
        [character],
        {"Healer One": BarId.FRONT},
    )

    providers = capabilities["major_courage"]

    assert len(providers) == 1
    assert providers[0].character_name == "Healer One"
    assert providers[0].role == Role.HEALER
    assert providers[0].effect.name == "major_courage"


def test_roster_preserves_multiple_providers_of_same_effect():
    healer = _character(
        "Healer One",
        Role.HEALER,
        EffectVariant(
            name="major_courage",
            layer=EffectLayer.SLOTTED,
            source="Healer Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        ),
    )

    tank = _character(
        "Tank One",
        Role.TANK,
        EffectVariant(
            name="major_courage",
            layer=EffectLayer.SLOTTED,
            source="Tank Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        ),
    )

    capabilities = RosterCapabilityResolver().resolve(
        [healer, tank],
        {
            "Healer One": BarId.FRONT,
            "Tank One": BarId.FRONT,
        },
    )

    providers = RosterCapabilityResolver.providers_for(
        capabilities,
        "major_courage",
    )

    assert len(providers) == 2
    assert {provider.character_name for provider in providers} == {
        "Healer One",
        "Tank One",
    }


def test_roster_does_not_merge_different_effects():
    healer = _character(
        "Healer One",
        Role.HEALER,
        EffectVariant(
            name="major_courage",
            layer=EffectLayer.SLOTTED,
            source="Healer Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        ),
    )

    tank = _character(
        "Tank One",
        Role.TANK,
        EffectVariant(
            name="major_protection",
            layer=EffectLayer.SLOTTED,
            source="Tank Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        ),
    )

    capabilities = RosterCapabilityResolver().resolve(
        [healer, tank],
        {
            "Healer One": BarId.FRONT,
            "Tank One": BarId.FRONT,
        },
    )

    assert set(capabilities) == {
        "major_courage",
        "major_protection",
    }

    assert len(capabilities["major_courage"]) == 1
    assert len(capabilities["major_protection"]) == 1