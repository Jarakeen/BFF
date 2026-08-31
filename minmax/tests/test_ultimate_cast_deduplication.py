from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.support_effect_resolver import resolve_effect_variants
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


def test_cast_layer_effect_on_ultimate_slot_resolves_only_once():
    force = EffectVariant(
        name="force",
        layer=EffectLayer.CAST,
        source="Aggressive Horn",
    )

    slots = tuple(
        SlottedSkill(
            skill_id=f"skill_{index}",
            skill_line_id="undaunted",
            is_cast=True,
        )
        for index in range(5)
    ) + (
        SlottedSkill(
            skill_id="aggressive_horn",
            skill_line_id="assault",
            is_ultimate=True,
            is_cast=True,
            effects=(force,),
        ),
    )

    build = CharacterBuild(
        name="Horn test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=slots,
        ),
    )

    resolved = resolve_effect_variants(build, BarId.FRONT)

    assert [effect.name for effect in resolved] == ["force"]
    assert [effect.source for effect in resolved] == ["Aggressive Horn"]
