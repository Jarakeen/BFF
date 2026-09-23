from __future__ import annotations

from minmax.core_stat_calculator import CoreStatCalculator
from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import CharacterProgression
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.stat_ids import StatId
from minmax.weapon_standing_passive_input_resolver import WeaponStandingPassiveInputResolver
from models.build_model import GearSlot, PlayerBuild


def _state(result: GearCalculationInputs):
    return CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )


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


def test_ambidextrous_remains_explicitly_unresolved():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Sword"),
    )
    result = WeaponStandingPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        ambidextrous_owned=True,
    )

    assert any("Ambidextrous" in item for item in result.unresolved)


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
