from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_availability import resolve_available_effects
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


def _filler(index: int, skill_line_id: str = "dual_wield") -> SlottedSkill:
    return SlottedSkill(skill_id=f"filler_{index}", skill_line_id=skill_line_id)


def _build_with_bars(front: Bar, back: Bar) -> CharacterBuild:
    return CharacterBuild(
        name="Availability Test",
        character_class=CharacterClass.WARDEN,
        role=Role.TANK,
        front_bar=front,
        back_bar=back,
    )


def test_slotted_skill_with_no_cast_still_produces_value():
    """
    A tank slots Revealing Flare purely for its passive/stat benefit and
    never casts it - the slotted-layer effect must still be available.
    """
    revealing_flare = SlottedSkill(
        skill_id="revealing_flare",
        skill_line_id="fighters_guild",
        is_cast=False,
        effects=(
            EffectVariant(
                name="minor_maim_uptime_support",
                layer=EffectLayer.SLOTTED,
                source="Revealing Flare",
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.SWORD),
        off_hand=Weapon(weapon_type=WeaponType.SHIELD),
        slots=(revealing_flare, _filler(1), _filler(2), _filler(3), _filler(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="fighters_guild", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=tuple(_filler(i) for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="dual_wield", is_ultimate=True),),
    )
    build = _build_with_bars(front, back)

    available = resolve_available_effects(build, BarId.FRONT)
    names = {effect.name for effect in available}

    assert "minor_maim_uptime_support" in names


def test_dd_flex_slot_for_crit_never_cast_still_produces_stat_value():
    flex_skill = SlottedSkill(
        skill_id="camouflaged_hunter_source",
        skill_line_id="assassination",
        is_cast=False,
        effects=(
            EffectVariant(
                name="weapon_critical_flat",
                layer=EffectLayer.SLOTTED,
                source="Poison Injection",
                magnitude=657,
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=(flex_skill,) + tuple(_filler(i) for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="assassination", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i) for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="dual_wield", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="DD flex", character_class=CharacterClass.NIGHTBLADE, role=Role.DD,
        front_bar=front, back_bar=back,
    )

    available = resolve_available_effects(build, BarId.FRONT)
    names = {effect.name for effect in available}

    assert "weapon_critical_flat" in names


def test_cast_effect_requires_active_bar_and_is_cast_true():
    cast_skill = SlottedSkill(
        skill_id="wall_of_frost",
        skill_line_id="winters_embrace",
        is_cast=True,
        effects=(
            EffectVariant(
                name="chilled_status", layer=EffectLayer.CAST, source="Wall of Frost"
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=(cast_skill,) + tuple(_filler(i, "restoration_staff") for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="winters_embrace", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF),
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    build = _build_with_bars(front, back)

    on_front = resolve_available_effects(build, BarId.FRONT)
    on_back = resolve_available_effects(build, BarId.BACK)

    assert "chilled_status" in {e.name for e in on_front}
    assert "chilled_status" not in {e.name for e in on_back}


def test_bar_specific_set_activation():
    """
    Front bar: Arena Restoration Staff. Back bar: Master's Architect Ice
    Staff. The Master's Architect proc is only available while the back
    bar is active, because that weapon is only equipped there.
    """
    masters_ice_staff = Weapon(
        weapon_type=WeaponType.FROST_STAFF,
        set_id="masters_architect",
        effects=(
            EffectVariant(
                name="major_slayer",
                layer=EffectLayer.PROC,
                source="Masters Architect",
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF, set_id="arena"),
        off_hand=None,
        slots=tuple(_filler(i, "restoration_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult", skill_line_id="restoration_staff", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=masters_ice_staff,
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    build = _build_with_bars(front, back)

    on_front = resolve_available_effects(build, BarId.FRONT)
    on_back = resolve_available_effects(build, BarId.BACK)

    assert "major_slayer" not in {e.name for e in on_front}
    assert "major_slayer" in {e.name for e in on_back}


def test_passive_skill_line_dependency():
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=(
            SlottedSkill(skill_id="deep_fissure", skill_line_id="earthen_heart"),
        )
        + tuple(_filler(i) for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="earthen_heart", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i) for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="dual_wield", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="Passive Dependency", character_class=CharacterClass.DRAGONKNIGHT,
        role=Role.TANK, front_bar=front, back_bar=back,
    )

    grant = PassiveGrant(
        skill_line_id="earthen_heart",
        effect=EffectVariant(
            name="helping_hands_healing_boost",
            layer=EffectLayer.PASSIVE,
            source="Helping Hands",
        ),
        requires_active_bar_representation=False,
    )

    with_line_owned = resolve_available_effects(build, BarId.BACK, passives=[grant])
    assert "helping_hands_healing_boost" in {e.name for e in with_line_owned}


def test_warden_class_line_ultimate_passive_interaction():
    """
    Warden slots a class-line ultimate purely because a class passive
    rewards representing that skill line on the active bar - even though
    the ultimate is never cast.
    """
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i) for i in range(5))
        + (
            SlottedSkill(
                skill_id="secluded_grove",
                skill_line_id="green_balance",
                is_ultimate=True,
                is_cast=False,
            ),
        ),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.DAGGER),
        slots=tuple(_filler(i) for i in range(5))
        + (SlottedSkill(skill_id="ult2", skill_line_id="dual_wield", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="Warden Line Rep", character_class=CharacterClass.WARDEN,
        role=Role.HEALER, front_bar=front, back_bar=back,
    )

    grant = PassiveGrant(
        skill_line_id="green_balance",
        effect=EffectVariant(
            name="green_balance_line_bonus",
            layer=EffectLayer.PASSIVE,
            source="Warden class passive",
        ),
        requires_active_bar_representation=True,
    )

    on_front = resolve_available_effects(build, BarId.FRONT, passives=[grant])
    on_back = resolve_available_effects(build, BarId.BACK, passives=[grant])

    assert "green_balance_line_bonus" in {e.name for e in on_front}
    assert "green_balance_line_bonus" not in {e.name for e in on_back}
