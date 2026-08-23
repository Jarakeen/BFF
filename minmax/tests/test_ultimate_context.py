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

# These tests exercise the generic bar/trigger-context ultimate resolution
# mechanism only. The ultimate skill and set names are deliberately
# fictional so they cannot be mistaken for a verified ESO fact - for a
# real, repository-traced ultimate/skill fact (Aggressive Horn grants
# Major Force), see test_character_build_real_data_integration.py. No
# real source data in this repository establishes an ultimate-to-set-proc
# relationship (e.g. for Master's Architect) - see that same file's
# report section for what is and is not available from current data.


def _filler(index: int, skill_line_id: str) -> SlottedSkill:
    return SlottedSkill(skill_id=f"filler_{index}", skill_line_id=skill_line_id)


def _fictional_ultimate_slot() -> SlottedSkill:
    """
    A fictional ultimate slotted on both bars. Its produced effects
    differ depending on which bar it's cast from and whether a fictional
    trigger condition is met there - modeled generically via
    EffectVariant.active_bar/trigger, never as a static
    "ultimate = fixed effect" property.
    """
    return SlottedSkill(
        skill_id="fictional_ultimate",
        skill_line_id="assault",
        is_ultimate=True,
        effects=(
            EffectVariant(
                name="fictional_group_buff",
                layer=EffectLayer.ULTIMATE,
                source="Fictional Ultimate Skill",
            ),
            EffectVariant(
                name="fictional_set_proc_buff",
                layer=EffectLayer.ULTIMATE,
                source="Fictional Gear Set",
                active_bar=BarId.BACK,
                trigger="cast_from_fictional_set_bar",
            ),
        ),
    )


def _build_with_ultimate_on_both_bars() -> CharacterBuild:
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF, set_id="fictional_set_a"),
        off_hand=None,
        slots=tuple(_filler(i, "restoration_staff") for i in range(5))
        + (_fictional_ultimate_slot(),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF, set_id="fictional_set_b"),
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5))
        + (_fictional_ultimate_slot(),),
    )
    return CharacterBuild(
        name="Ultimate Bar Context",
        character_class=CharacterClass.TEMPLAR,
        role=Role.HEALER,
        front_bar=front,
        back_bar=back,
    )


def test_ultimate_cast_from_correct_bar_with_trigger_produces_bonus_effect():
    build = _build_with_ultimate_on_both_bars()

    result = resolve_ultimate_cast_effects(
        build, BarId.BACK, trigger="cast_from_fictional_set_bar"
    )
    names = {effect.name for effect in result}

    assert "fictional_group_buff" in names
    assert "fictional_set_proc_buff" in names


def test_ultimate_cast_from_wrong_bar_does_not_produce_bar_locked_effect():
    build = _build_with_ultimate_on_both_bars()

    result = resolve_ultimate_cast_effects(
        build, BarId.FRONT, trigger="cast_from_fictional_set_bar"
    )
    names = {effect.name for effect in result}

    assert "fictional_group_buff" in names
    assert "fictional_set_proc_buff" not in names


def test_ultimate_cast_from_correct_bar_without_matching_trigger_omits_bonus():
    build = _build_with_ultimate_on_both_bars()

    result = resolve_ultimate_cast_effects(build, BarId.BACK, trigger=None)
    names = {effect.name for effect in result}

    assert "fictional_group_buff" in names
    assert "fictional_set_proc_buff" not in names


def test_no_ultimate_slotted_produces_no_effects():
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i, "dual_wield") for i in range(6)),  # no ultimate flagged
    )
    build = CharacterBuild(
        name="No Ultimate",
        character_class=CharacterClass.TEMPLAR,
        role=Role.DD,
        front_bar=front,
        back_bar=None,
    )

    # Bar itself is invalid (no ultimate), but the resolver should still
    # degrade gracefully rather than raising.
    result = resolve_ultimate_cast_effects(build, BarId.FRONT)
    assert result == ()
