from pathlib import Path

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.support_effect_resolver_factory import (
    build_db_backed_support_effect_resolver,
)
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


DB_PATH = Path("data/eso.db")


def _slots(line: str) -> tuple[SlottedSkill, ...]:
    return tuple(
        SlottedSkill(skill_id=f"skill_{index}", skill_line_id=line)
        for index in range(5)
    ) + (
        SlottedSkill(skill_id="ultimate", skill_line_id=line, is_ultimate=True),
    )


def test_db_backed_factory_bridges_active_bar_crushing_enchantment():
    build = CharacterBuild(
        name="Crushing Bridge",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=_slots("restoration_staff"),
        ),
        back_bar=Bar(
            bar_id=BarId.BACK,
            main_hand=Weapon(
                weapon_type=WeaponType.FROST_STAFF,
                enchantment_item_id=26845,
            ),
            off_hand=None,
            slots=_slots("destruction_staff"),
        ),
    )

    resolver = build_db_backed_support_effect_resolver(DB_PATH)

    on_front = resolver.resolve(build, BarId.FRONT).all()
    on_back = resolver.resolve(build, BarId.BACK).all()

    assert not any(
        effect.effect_type == "physical_spell_resistance_reduction"
        for effect in on_front
    )
    crushing = [
        effect
        for effect in on_back
        if effect.effect_type == "physical_spell_resistance_reduction"
    ]
    assert len(crushing) == 1
    assert crushing[0].source == "Glyph of Crushing"
