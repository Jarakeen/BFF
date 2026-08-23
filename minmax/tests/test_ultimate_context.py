from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_availability import resolve_ultimate_cast_effects
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


def _filler(index: int, skill_line_id: str) -> SlottedSkill:
    return SlottedSkill(skill_id=f"filler_{index}", skill_line_id=skill_line_id)


def _horn_slot() -> SlottedSkill:
    """
    Aggressive Horn, slotted as the ultimate on both bars. Its produced
    effects differ depending on which bar it's cast from and whether the
    Master's Architect trigger condition is met there - modeled generically
    via EffectVariant.active_bar/trigger, never as a static "ultimate =
    Major Slayer" property.
    """
    return SlottedSkill(
        skill_id="aggressive_horn",
        skill_line_id="assault",
        is_ultimate=True,
        effects=(
            EffectVariant(
                name="major_courage",
                layer=EffectLayer.ULTIMATE,
                source="Aggressive Horn",
            ),
            EffectVariant(
                name="major_slayer",
                layer=EffectLayer.ULTIMATE,
                source="Masters Architect",
                active_bar=BarId.BACK,
                trigger="cast_from_masters_architect_bar",
            ),
        ),
    )


def _build_with_horn_on_both_bars() -> CharacterBuild:
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF, set_id="arena"),
        off_hand=None,
        slots=tuple(_filler(i, "restoration_staff") for i in range(5)) + (_horn_slot(),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF, set_id="masters_architect"),
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5)) + (_horn_slot(),),
    )
    return CharacterBuild(
        name="Horn Bar Context", character_class=CharacterClass.TEMPLAR,
        role=Role.HEALER, front_bar=front, back_bar=back,
    )


def test_ultimate_cast_from_correct_bar_with_trigger_produces_bonus_effect():
    build = _build_with_horn_on_both_bars()

    result = resolve_ultimate_cast_effects(
        build, BarId.BACK, trigger="cast_from_masters_architect_bar"
    )
    names = {effect.name for effect in result}

    assert "major_courage" in names
    assert "major_slayer" in names


def test_ultimate_cast_from_wrong_bar_does_not_produce_bar_locked_effect():
    build = _build_with_horn_on_both_bars()

    result = resolve_ultimate_cast_effects(
        build, BarId.FRONT, trigger="cast_from_masters_architect_bar"
    )
    names = {effect.name for effect in result}

    assert "major_courage" in names
    assert "major_slayer" not in names


def test_ultimate_cast_from_correct_bar_without_matching_trigger_omits_bonus():
    build = _build_with_horn_on_both_bars()

    result = resolve_ultimate_cast_effects(build, BarId.BACK, trigger=None)
    names = {effect.name for effect in result}

    assert "major_courage" in names
    assert "major_slayer" not in names


def test_no_ultimate_slotted_produces_no_effects():
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i, "dual_wield") for i in range(6)),  # no ultimate flagged
    )
    build = CharacterBuild(
        name="No Ultimate", character_class=CharacterClass.TEMPLAR,
        role=Role.DD, front_bar=front, back_bar=None,
    )

    # Bar itself is invalid (no ultimate), but the resolver should still
    # degrade gracefully rather than raising.
    result = resolve_ultimate_cast_effects(build, BarId.FRONT)
    assert result == ()
