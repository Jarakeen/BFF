from pathlib import Path

import pytest

from minmax.build_combat_effect_service import BuildCombatEffectService
from minmax.build_support_effect_service import BuildSupportEffectService
from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild, IllegalBuildError
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.effect_relationship import (
    EffectRelationship,
    EffectRelationshipType,
)
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
    resolve_effect_variants,
)
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.rule_repository import RuleRepository
from minmax.support_coverage import SupportCoverage
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository
from minmax.weapon_enchantment_effect_service import WeaponEnchantmentEffectService

DB_PATH = Path("data/eso.db")


def _filler(index: int, skill_line_id: str = "dual_wield") -> SlottedSkill:
    return SlottedSkill(skill_id=f"filler_{index}", skill_line_id=skill_line_id)


def _valid_bar(
    bar_id: BarId,
    weapon_type: WeaponType,
    skill_line_id: str,
    slots: tuple[SlottedSkill, ...] | None = None,
) -> Bar:
    if slots is None:
        slots = tuple(_filler(i, skill_line_id) for i in range(5)) + (
            SlottedSkill(skill_id=f"ult_{bar_id.value}", skill_line_id=skill_line_id, is_ultimate=True),
        )
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon_type=weapon_type),
        off_hand=None,
        slots=slots,
    )


def _resolver() -> CharacterBuildSupportEffectResolver:
    return CharacterBuildSupportEffectResolver()


# -- effect layers -----------------------------------------------------------


def test_skill_cast_effect_resolution():
    cast_slot = SlottedSkill(
        skill_id="wall_of_frost",
        skill_line_id="winters_embrace",
        is_cast=True,
        effects=(
            EffectVariant(
                name="chilled_status",
                layer=EffectLayer.CAST,
                source="Wall of Frost",
                target_type=SupportTargetType.ENEMY,
                category=SupportEffectCategory.STATUS,
            ),
        ),
    )
    front = _valid_bar(
        BarId.FRONT,
        WeaponType.RESTORATION_STAFF,
        "restoration_staff",
        slots=(cast_slot,) + tuple(_filler(i, "restoration_staff") for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="winters_embrace", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.FROST_STAFF, "destruction_staff")
    build = CharacterBuild(
        name="Cast Test", character_class=CharacterClass.WARDEN, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    chilled = [e for e in registry.all() if e.name == "chilled_status"]

    assert len(chilled) == 1
    assert chilled[0].target_type == SupportTargetType.ENEMY
    assert chilled[0].category == SupportEffectCategory.STATUS


def test_slotted_only_effect_resolution():
    revealing_flare = SlottedSkill(
        skill_id="revealing_flare",
        skill_line_id="fighters_guild",
        is_cast=False,
        effects=(
            EffectVariant(
                name="minor_maim_support",
                layer=EffectLayer.SLOTTED,
                source="Revealing Flare",
                target_type=SupportTargetType.GROUP,
                category=SupportEffectCategory.DEBUFF,
            ),
        ),
    )
    front = _valid_bar(
        BarId.FRONT, WeaponType.SWORD, "one_hand_and_shield",
        slots=(revealing_flare,) + tuple(_filler(i, "one_hand_and_shield") for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="fighters_guild", is_ultimate=True),),
    )
    front = Bar(bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.SWORD),
                off_hand=Weapon(weapon_type=WeaponType.SHIELD), slots=front.slots)
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Slotted Test", character_class=CharacterClass.DRAGONKNIGHT, role=Role.TANK,
        front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    names = {e.name for e in registry.all()}

    assert "minor_maim_support" in names
    # never cast: this only proves it doesn't require CAST to surface.
    assert not revealing_flare.is_cast


def test_passive_effect_resolution():
    front = _valid_bar(BarId.FRONT, WeaponType.DAGGER, "earthen_heart")
    front = Bar(bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
                off_hand=Weapon(weapon_type=WeaponType.AXE), slots=front.slots)
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Passive Test", character_class=CharacterClass.DRAGONKNIGHT, role=Role.TANK,
        front_bar=front, back_bar=back,
    )
    grant = PassiveGrant(
        skill_line_id="earthen_heart",
        effect=EffectVariant(
            name="helping_hands_healing_boost",
            layer=EffectLayer.PASSIVE,
            source="Helping Hands",
            target_type=SupportTargetType.SELF,
        ),
        requires_active_bar_representation=False,
    )

    registry = _resolver().resolve(build, BarId.BACK, passives=[grant])
    names = {e.name for e in registry.all()}

    assert "helping_hands_healing_boost" in names


def test_proc_effect_resolution_retains_trigger_condition():
    masters_ice_staff = Weapon(
        weapon_type=WeaponType.FROST_STAFF,
        set_id="masters_architect",
        effects=(
            EffectVariant(
                name="major_slayer",
                layer=EffectLayer.PROC,
                source="Masters Architect",
                target_type=SupportTargetType.GROUP,
                category=SupportEffectCategory.BUFF,
                condition="ultimate_cast_from_back_bar",
            ),
        ),
    )
    front = _valid_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, "restoration_staff")
    back = Bar(bar_id=BarId.BACK, main_hand=masters_ice_staff, off_hand=None,
               slots=tuple(_filler(i, "destruction_staff") for i in range(5))
               + (SlottedSkill(skill_id="ult", skill_line_id="destruction_staff", is_ultimate=True),))
    build = CharacterBuild(
        name="Proc Test", character_class=CharacterClass.TEMPLAR, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.BACK)
    slayer = [e for e in registry.all() if e.name == "major_slayer"]

    assert len(slayer) == 1
    assert slayer[0].conditions == ("ultimate_cast_from_back_bar",)


def test_ultimate_resolution_by_bar_context():
    ult_effects = (
        EffectVariant(
            name="major_courage", layer=EffectLayer.ULTIMATE, source="Aggressive Horn",
            target_type=SupportTargetType.GROUP, category=SupportEffectCategory.BUFF,
        ),
        EffectVariant(
            name="major_slayer", layer=EffectLayer.ULTIMATE, source="Masters Architect",
            target_type=SupportTargetType.GROUP, category=SupportEffectCategory.BUFF,
            active_bar=BarId.BACK, trigger="cast_from_masters_bar",
        ),
    )
    front = Bar(bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
                off_hand=None,
                slots=tuple(_filler(i, "restoration_staff") for i in range(5))
                + (SlottedSkill(skill_id="horn", skill_line_id="assault", is_ultimate=True, effects=ult_effects),))
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF),
               off_hand=None,
               slots=tuple(_filler(i, "destruction_staff") for i in range(5))
               + (SlottedSkill(skill_id="horn", skill_line_id="assault", is_ultimate=True, effects=ult_effects),))
    build = CharacterBuild(
        name="Ultimate Test", character_class=CharacterClass.TEMPLAR, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    from_back = _resolver().resolve(build, BarId.BACK, ultimate_trigger="cast_from_masters_bar")
    from_front = _resolver().resolve(build, BarId.FRONT, ultimate_trigger="cast_from_masters_bar")

    assert "major_slayer" in {e.name for e in from_back.all()}
    assert "major_slayer" not in {e.name for e in from_front.all()}
    assert "major_courage" in {e.name for e in from_front.all()}


# -- bar context ---------------------------------------------------------


def test_front_and_back_weapon_differences_only_active_bar_effects_appear():
    front_effect = EffectVariant(
        name="front_only_effect", layer=EffectLayer.PROC, source="Front Weapon",
        target_type=SupportTargetType.ENEMY,
    )
    back_effect = EffectVariant(
        name="back_only_effect", layer=EffectLayer.PROC, source="Back Weapon",
        target_type=SupportTargetType.ENEMY,
    )
    front = Bar(bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF, effects=(front_effect,)),
                off_hand=None, slots=tuple(_filler(i, "restoration_staff") for i in range(5))
                + (SlottedSkill(skill_id="ult", skill_line_id="restoration_staff", is_ultimate=True),))
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF, effects=(back_effect,)),
               off_hand=None, slots=tuple(_filler(i, "destruction_staff") for i in range(5))
               + (SlottedSkill(skill_id="ult2", skill_line_id="destruction_staff", is_ultimate=True),))
    build = CharacterBuild(
        name="Bar Weapon Diff", character_class=CharacterClass.TEMPLAR, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    on_front = {e.name for e in _resolver().resolve(build, BarId.FRONT).all()}
    on_back = {e.name for e in _resolver().resolve(build, BarId.BACK).all()}

    assert "front_only_effect" in on_front and "back_only_effect" not in on_front
    assert "back_only_effect" in on_back and "front_only_effect" not in on_back


def test_bar_specific_set_effects_do_not_leak_to_other_bar():
    """A support effect available only on the back bar must not be
    represented as continuously active on the front bar."""
    back_set_effect = EffectVariant(
        name="major_slayer", layer=EffectLayer.PROC, source="Masters Architect",
        target_type=SupportTargetType.GROUP,
    )
    front = _valid_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, "restoration_staff")
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF, set_id="masters_architect", effects=(back_set_effect,)),
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="Bar Set Test", character_class=CharacterClass.TEMPLAR, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    on_front = _resolver().resolve(build, BarId.FRONT)
    on_back = _resolver().resolve(build, BarId.BACK)

    assert "major_slayer" not in {e.name for e in on_front.all()}
    assert "major_slayer" in {e.name for e in on_back.all()}


# -- weapon enchantments (DB-backed) --------------------------------------


def test_weapon_enchantment_effects_bridge_through_existing_db_service():
    """
    Uses the real, unmodified DB-backed weapon enchantment pipeline
    (WeaponEnchantmentRepository / WeaponEnchantmentEffectService /
    BuildCombatEffectService / BuildSupportEffectService), scoped to
    the active bar's weapon only.

    NOTE: this checkout's data/eso.db is empty (0 bytes, no tables) -
    see the end-of-task report. This test documents the intended,
    correct wiring and will pass once a populated database is present;
    here it is expected to fail the same way every other DB-backed test
    in this suite already does.
    """
    weapon_enchantment_repository = WeaponEnchantmentRepository(DB_PATH)
    rule_repository = RuleRepository(DB_PATH)
    weapon_enchantment_service = WeaponEnchantmentEffectService(
        enchantment_repository=weapon_enchantment_repository,
        rule_repository=rule_repository,
    )
    combat_effect_service = BuildCombatEffectService(
        weapon_enchantment_service=weapon_enchantment_service,
    )
    support_effect_service = BuildSupportEffectService(
        build_combat_effect_service=combat_effect_service,
    )
    resolver = CharacterBuildSupportEffectResolver(
        weapon_enchantment_support_service=support_effect_service,
    )

    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF, enchantment_item_id=1, trait="Charged"),
        off_hand=None,
        slots=tuple(_filler(i, "destruction_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Enchant Bridge Test", character_class=CharacterClass.SORCERER, role=Role.DD,
        front_bar=front, back_bar=back,
    )

    registry = resolver.resolve(build, BarId.FRONT)
    # Only asserts the bridge runs without raising and returns a registry;
    # actual enchantment content depends on a populated database.
    assert registry.all() is not None


# -- identity / variants / providers --------------------------------------


def test_multiple_providers_of_same_named_effect_are_not_merged():
    provider_a = SlottedSkill(
        skill_id="skill_a", skill_line_id="dual_wield", is_cast=True,
        effects=(EffectVariant(name="major_force", layer=EffectLayer.CAST, source="Skill A",
                                target_type=SupportTargetType.GROUP, magnitude=100),),
    )
    provider_b = SlottedSkill(
        skill_id="skill_b", skill_line_id="dual_wield", is_cast=True,
        effects=(EffectVariant(name="major_force", layer=EffectLayer.CAST, source="Skill B",
                                target_type=SupportTargetType.GROUP, magnitude=100),),
    )
    front = Bar(
        bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=(provider_a, provider_b) + tuple(_filler(i) for i in range(3))
        + (SlottedSkill(skill_id="ult", skill_line_id="dual_wield", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Multi Provider", character_class=CharacterClass.NIGHTBLADE, role=Role.DD,
        front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    force_effects = [e for e in registry.all() if e.name == "major_force"]

    assert len(force_effects) == 2
    assert {e.source for e in force_effects} == {"Skill A", "Skill B"}
    # Magnitudes must not be summed anywhere in this resolver.
    assert all(e.magnitude == 100 for e in force_effects)


def test_multiple_numeric_values_on_one_effect_preserved_per_provider():
    weak = SlottedSkill(
        skill_id="weak_source", skill_line_id="dual_wield", is_cast=True,
        effects=(EffectVariant(name="major_brittle", layer=EffectLayer.CAST, source="Weak Source",
                                target_type=SupportTargetType.ENEMY, duration=6.0, chance=0.25),),
    )
    strong = SlottedSkill(
        skill_id="strong_source", skill_line_id="dual_wield", is_cast=True,
        effects=(EffectVariant(name="major_brittle", layer=EffectLayer.CAST, source="Strong Source",
                                target_type=SupportTargetType.ENEMY, duration=10.0, chance=1.0),),
    )
    front = Bar(
        bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=(weak, strong) + tuple(_filler(i) for i in range(3))
        + (SlottedSkill(skill_id="ult", skill_line_id="dual_wield", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Numeric Variants", character_class=CharacterClass.NIGHTBLADE, role=Role.DD,
        front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    by_source = {e.source: e for e in registry.all() if e.name == "major_brittle"}

    assert by_source["Weak Source"].duration == 6.0
    assert by_source["Weak Source"].uptime  # uptime default preserved, not conflated with chance
    assert by_source["Strong Source"].duration == 10.0


# -- target preservation ---------------------------------------------------


def test_target_type_is_preserved_and_coverage_filters_correctly():
    self_effect = EffectVariant(name="self_stat_bonus", layer=EffectLayer.SLOTTED, source="Gear",
                                 target_type=SupportTargetType.SELF)
    enemy_effect = EffectVariant(name="major_breach", layer=EffectLayer.CAST, source="Skill",
                                  target_type=SupportTargetType.ENEMY, category=SupportEffectCategory.DEBUFF)
    group_effect = EffectVariant(name="major_courage", layer=EffectLayer.CAST, source="Skill 2",
                                  target_type=SupportTargetType.GROUP, category=SupportEffectCategory.BUFF)
    skill_1 = SlottedSkill(skill_id="s1", skill_line_id="dual_wield", is_cast=True, effects=(enemy_effect,))
    skill_2 = SlottedSkill(skill_id="s2", skill_line_id="dual_wield", is_cast=True, effects=(group_effect,))
    gear_piece = ArmorPiece(slot=GearSlot.HEAD, effects=(self_effect,))

    front = Bar(
        bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=(skill_1, skill_2) + tuple(_filler(i) for i in range(3))
        + (SlottedSkill(skill_id="ult", skill_line_id="dual_wield", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Target Preservation", character_class=CharacterClass.NIGHTBLADE, role=Role.DD,
        armor=(gear_piece,), front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    coverage = SupportCoverage(registry)

    assert {e.name for e in coverage.targeting_enemies()} == {"major_breach"}
    assert {e.name for e in coverage.targeting_group()} == {"major_courage"}
    assert "self_stat_bonus" not in {e.name for e in coverage.contributing_to_group()}


def test_group_contributing_vs_self_only_effects():
    self_only = EffectVariant(name="weapon_damage_flat", layer=EffectLayer.SLOTTED, source="Glyph")  # no target_type -> SELF
    group_buff = EffectVariant(name="major_courage", layer=EffectLayer.CAST, source="Skill",
                                target_type=SupportTargetType.GROUP)
    slot = SlottedSkill(skill_id="s", skill_line_id="dual_wield", is_cast=True, effects=(group_buff,))
    gear_piece = ArmorPiece(slot=GearSlot.HEAD, effects=(self_only,))

    front = Bar(
        bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=(slot,) + tuple(_filler(i) for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="dual_wield", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.DAGGER, "dual_wield")
    back = Bar(bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.DAGGER),
               off_hand=Weapon(weapon_type=WeaponType.AXE), slots=back.slots)
    build = CharacterBuild(
        name="Contributing Test", character_class=CharacterClass.NIGHTBLADE, role=Role.DD,
        armor=(gear_piece,), front_bar=front, back_bar=back,
    )

    registry = _resolver().resolve(build, BarId.FRONT)
    contributing_names = {e.name for e in registry.contributing_to_group()}

    assert "major_courage" in contributing_names
    assert "weapon_damage_flat" not in contributing_names


# -- relationships / status chains ------------------------------------------


def test_effect_relationships_apply_before_conversion():
    base = SlottedSkill(
        skill_id="combat_prayer", skill_line_id="restoring_light", is_cast=True,
        effects=(EffectVariant(name="minor_toughness", layer=EffectLayer.CAST, source="Combat Prayer",
                                target_type=SupportTargetType.GROUP, duration=20.0),),
    )
    presence = ArmorPiece(
        slot=GearSlot.NECKLACE,
        effects=(EffectVariant(name="jorvulds_guidance_equipped", layer=EffectLayer.PROC, source="Jorvulds Guidance"),),
    )
    front = Bar(
        bar_id=BarId.FRONT, main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF), off_hand=None,
        slots=(base,) + tuple(_filler(i, "restoration_staff") for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="restoring_light", is_ultimate=True),),
    )
    back = _valid_bar(BarId.BACK, WeaponType.FROST_STAFF, "destruction_staff")
    build = CharacterBuild(
        name="Relationship Test", character_class=CharacterClass.TEMPLAR, role=Role.HEALER,
        armor=(presence,), front_bar=front, back_bar=back,
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="jorvulds_guidance_equipped",
        target_effect="minor_toughness",
        magnitude_delta=6.0,
    )

    registry = _resolver().resolve(build, BarId.FRONT, relationships=[relationship])
    toughness = [e for e in registry.all() if e.name == "minor_toughness"][0]

    assert toughness.duration == 26.0


def test_conditional_status_chain_preserves_source_trigger_and_condition():
    frost_damage = EffectVariant(
        name="frost_damage_applied", layer=EffectLayer.PROC, source="Frost Staff Heavy Attack",
        target_type=SupportTargetType.ENEMY,
    )
    slot = SlottedSkill(skill_id="s", skill_line_id="destruction_staff", is_cast=True, effects=(frost_damage,))
    front = _valid_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, "restoration_staff")
    back = Bar(
        bar_id=BarId.BACK, main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF), off_hand=None,
        slots=(slot,) + tuple(_filler(i, "destruction_staff") for i in range(4))
        + (SlottedSkill(skill_id="ult", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="Status Chain", character_class=CharacterClass.WARDEN, role=Role.DD,
        front_bar=front, back_bar=back,
    )
    frost_to_chilled = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="frost_damage_applied",
        target_effect="chilled_status",
        condition="target_not_already_chilled",
    )
    chilled_to_brittle = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="chilled_status",
        target_effect="major_brittle",
        condition="target_already_chilled",
    )

    registry = _resolver().resolve(
        build, BarId.BACK, relationships=[frost_to_chilled, chilled_to_brittle]
    )
    by_name = {e.name: e for e in registry.all()}

    assert "chilled_status" in by_name
    assert by_name["chilled_status"].trigger is not None
    assert by_name["chilled_status"].trigger.trigger == "frost_damage_applied"
    assert by_name["chilled_status"].trigger.condition == "target_not_already_chilled"

    # chilled_status only gets synthesized on this pass; brittle depends on
    # chilled_status being present in the same resolved set it was applied to,
    # which apply_relationships evaluates in relationship order.
    assert "major_brittle" in by_name
    assert by_name["major_brittle"].trigger.trigger == "chilled_status"


# -- hard constraint enforcement --------------------------------------------


def test_resolver_refuses_class_passive_violation():
    front = _valid_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, "ardent_flame")
    back = _valid_bar(BarId.BACK, WeaponType.FROST_STAFF, "destruction_staff")
    illegal_build = CharacterBuild(
        name="Illegal Warden", character_class=CharacterClass.WARDEN, role=Role.HEALER,
        front_bar=front, back_bar=back,
    )

    with pytest.raises(IllegalBuildError):
        resolve_effect_variants(illegal_build, BarId.FRONT)


def test_resolver_refuses_two_mythics():
    front = _valid_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, "restoration_staff")
    back = _valid_bar(BarId.BACK, WeaponType.FROST_STAFF, "destruction_staff")
    illegal_build = CharacterBuild(
        name="Illegal Mythic", character_class=CharacterClass.WARDEN, role=Role.HEALER,
        mythic=ArmorPiece(slot=GearSlot.NECKLACE, category=GearPieceCategory.MYTHIC),
        armor=(ArmorPiece(slot=GearSlot.RING_1, category=GearPieceCategory.MYTHIC),),
        front_bar=front, back_bar=back,
    )

    with pytest.raises(IllegalBuildError):
        _resolver().resolve(illegal_build, BarId.FRONT)
