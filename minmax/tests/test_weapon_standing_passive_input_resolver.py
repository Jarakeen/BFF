from __future__ import annotations

from minmax.core_stat_calculator import CoreStatCalculator
from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import CharacterProgression
from minmax.gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from minmax.stat_ids import StatId
from minmax.weapon_standing_passive_input_resolver import WeaponStandingPassiveInputResolver
from models.build_model import GearSlot, PlayerBuild


def _state(result: GearCalculationInputs):
    return CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )



def test_bow_accuracy_applies_reviewed_rank_two_critical_rating():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Bow"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        bow_accuracy_owned=True,
    )

    state = _state(result)
    expected = 0.10 + GearStatInputResolver.critical_rating_to_ratio(1314.0)
    assert abs(state.derived[StatId.WEAPON_CRITICAL].final_value - expected) < 1e-12
    assert abs(state.derived[StatId.SPELL_CRITICAL].final_value - expected) < 1e-12
    assert not result.unresolved


def test_bow_accuracy_does_not_apply_when_bow_is_not_on_active_bar():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
        BackBarWeapon=GearSlot(WeaponType="Bow"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        bow_accuracy_owned=True,
    )

    state = _state(result)
    assert state.derived[StatId.WEAPON_CRITICAL].final_value == 0.10
    assert state.derived[StatId.SPELL_CRITICAL].final_value == 0.10

def test_dual_swords_apply_reviewed_twin_blade_flat_damage():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Sword"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        twin_blade_and_blunt_owned=True,
    )

    state = _state(result)
    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1128
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1128
    assert not result.unresolved


def test_twin_blade_non_sword_branch_fails_closed():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Dagger"),
        FrontBarOffHand=GearSlot(WeaponType="Axe"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        twin_blade_and_blunt_owned=True,
    )

    assert any("Twin Blade and Blunt standing effect" in item for item in result.unresolved)


def test_ambidextrous_applies_reviewed_three_percent_of_offhand_weapon_damage():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
        FrontBarOffHand=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        ambidextrous_owned=True,
    )

    state = _state(result)
    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1040.05
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1040.05
    assert not result.unresolved


def test_ambidextrous_fails_closed_without_verified_offhand_item_power():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Sword"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        ambidextrous_owned=True,
    )

    assert any("requires verified CP160 Gold off-hand" in item for item in result.unresolved)


def test_greatsword_applies_reviewed_heavy_weapons_flat_damage():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Greatsword"))
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        heavy_weapons_owned=True,
    )

    state = _state(result)
    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1129
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1129
    assert not result.unresolved


def test_heavy_weapons_non_greatsword_branch_fails_closed():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Maul"))
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        heavy_weapons_owned=True,
    )

    assert any("Heavy Weapons standing effect" in item for item in result.unresolved)


def test_heavy_weapons_legacy_two_handed_identity_fails_closed():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Two-Handed"))
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        heavy_weapons_owned=True,
    )

    assert any("requires a concrete weapon subtype" in item for item in result.unresolved)


class _SkillLineRepository:
    _MAX = {
        "Twin Blade and Blunt": 2,
        "Ambidextrous": 2,
        "Heavy Weapons": 2,
        "Accuracy": 2,
    }

    def passive_max_rank(self, passive_name: str):
        return self._MAX.get(passive_name)

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = ""):
        return None


def test_phase5_context_applies_owned_dual_sword_twin_blade_without_ambidextrous_guess():
    from minmax.context_factory import BuildCalculationContextFactory

    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
        FrontBarOffHand=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
    )
    context = BuildCalculationContextFactory(
        skill_line_repository=_SkillLineRepository(),
    ).build(
        character_id="character",
        build_id="dual-sword-passive",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Dual Wield",),
            passive_ranks={
                "Twin Blade and Blunt": 2,
                "Ambidextrous": 0,
            },
        ),
    )

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1699
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1699
    assert not any("Twin Blade and Blunt" in item for item in context.unresolved_gear_effects)


def test_phase5_context_applies_owned_ambidextrous_from_verified_offhand_power():
    from minmax.context_factory import BuildCalculationContextFactory

    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
        FrontBarOffHand=GearSlot(
            WeaponType="Sword",
            Quality="Gold",
            Level="CP160",
        ),
    )
    context = BuildCalculationContextFactory(
        skill_line_repository=_SkillLineRepository(),
    ).build(
        character_id="character",
        build_id="dual-sword-ambidextrous",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Dual Wield",),
            passive_ranks={
                "Twin Blade and Blunt": 2,
                "Ambidextrous": 2,
            },
        ),
    )

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1739.05
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1739.05
    assert not any("Ambidextrous" in item for item in context.unresolved_gear_effects)


def test_phase5_context_applies_owned_greatsword_heavy_weapons():
    from minmax.context_factory import BuildCalculationContextFactory

    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Greatsword",
            Quality="Gold",
            Level="CP160",
        ),
    )
    context = BuildCalculationContextFactory(
        skill_line_repository=_SkillLineRepository(),
    ).build(
        character_id="character",
        build_id="greatsword-heavy-weapons",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Two Handed",),
            passive_ranks={"Heavy Weapons": 2},
        ),
    )

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1700
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1700
    assert not any("Heavy Weapons" in item for item in context.unresolved_gear_effects)


def test_phase5_context_applies_owned_bow_accuracy_only_on_active_bow_bar():
    from minmax.context_factory import BuildCalculationContextFactory

    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Bow",
            Quality="Gold",
            Level="CP160",
        ),
        BackBarWeapon=GearSlot(
            WeaponType="Greatsword",
            Quality="Gold",
            Level="CP160",
        ),
    )
    factory = BuildCalculationContextFactory(
        skill_line_repository=_SkillLineRepository(),
    )
    progression = CharacterProgression(
        owned_skill_lines=("Bow",),
        passive_ranks={"Accuracy": 2},
    )

    front = factory.build(
        character_id="character",
        build_id="bow-accuracy-front",
        build=build,
        progression=progression,
        active_bar="front",
    )
    back = factory.build(
        character_id="character",
        build_id="bow-accuracy-back",
        build=build,
        progression=progression,
        active_bar="back",
    )

    expected = 0.10 + GearStatInputResolver.critical_rating_to_ratio(1314.0)
    assert abs(front.core_state.derived[StatId.WEAPON_CRITICAL].final_value - expected) < 1e-12
    assert abs(front.core_state.derived[StatId.SPELL_CRITICAL].final_value - expected) < 1e-12
    assert back.core_state.derived[StatId.WEAPON_CRITICAL].final_value == 0.10
    assert back.core_state.derived[StatId.SPELL_CRITICAL].final_value == 0.10
