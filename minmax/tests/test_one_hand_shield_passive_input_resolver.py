from __future__ import annotations

import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.one_hand_shield_passive_input_resolver import OneHandShieldPassiveInputResolver
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


def _explicit_sword_and_shield() -> PlayerBuild:
    return PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
    )


def test_explicit_one_hand_and_shield_applies_verified_standing_passives():
    result = OneHandShieldPassiveInputResolver().apply(
        GearCalculationInputs(),
        _explicit_sword_and_shield(),
        active_bar="front",
        passives_owned=True,
    )

    assert result.core.block_cost.sequential_modifiers[-1].label == "One Hand and Shield: Fortress"
    assert result.core.block_cost.sequential_modifiers[-1].percent == pytest.approx(-0.36)
    assert result.core.block_mitigation.amount_blocked_modifiers[-1] == (
        "One Hand and Shield: Sword and Board",
        pytest.approx(0.20),
    )
    assert result.core.weapon_damage.percent[-1].value == pytest.approx(0.05)
    assert result.core.spell_damage.percent[-1].value == pytest.approx(0.05)

    state = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )
    assert state.derived[StatId.BLOCK_COST].final_value == 1120
    assert state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.60)
    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1050
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1050


def test_legacy_one_hand_and_shield_bar_is_supported():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="One Hand and Shield"))
    result = OneHandShieldPassiveInputResolver().apply(
        GearCalculationInputs(), build, passives_owned=True
    )
    assert result.core.block_cost.sequential_modifiers
    assert result.core.block_mitigation.amount_blocked_modifiers


def test_equipment_does_not_apply_one_hand_shield_passives_without_ownership():
    original = GearCalculationInputs()
    result = OneHandShieldPassiveInputResolver().apply(
        original, _explicit_sword_and_shield(), passives_owned=False
    )
    assert result == original


def test_ownership_does_not_apply_without_shield_on_active_bar():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Sword"))
    original = GearCalculationInputs()
    result = OneHandShieldPassiveInputResolver().apply(
        original, build, active_bar="front", passives_owned=True
    )
    assert result == original


def test_defensive_stance_applies_when_slotted_with_shield_without_passive_ownership():
    build = _explicit_sword_and_shield()
    build.FrontBarSkills[0] = "Defensive Stance"

    result = OneHandShieldPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        passives_owned=False,
    )

    assert result.core.block_cost.sequential_modifiers[-1].label == "One Hand and Shield: Defensive Stance"
    assert result.core.block_cost.sequential_modifiers[-1].percent == pytest.approx(-0.10)
    assert result.core.block_mitigation.amount_blocked_modifiers[-1] == (
        "One Hand and Shield: Defensive Stance",
        pytest.approx(0.10),
    )

    state = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )
    assert state.derived[StatId.BLOCK_COST].final_value == 1575
    assert state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.55)


def test_defensive_stance_stacks_after_fortress_and_with_sword_and_board_bucket():
    build = _explicit_sword_and_shield()
    build.FrontBarSkills[0] = "Defensive Stance"

    result = OneHandShieldPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        passives_owned=True,
    )
    state = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=result.core,
    )

    assert state.derived[StatId.BLOCK_COST].final_value == 1008
    assert state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.65)
    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1050
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1050


def test_defensive_stance_only_checks_the_active_bar():
    build = _explicit_sword_and_shield()
    build.BackBarSkills[0] = "Defensive Stance"

    original = GearCalculationInputs()
    result = OneHandShieldPassiveInputResolver().apply(
        original,
        build,
        active_bar="front",
        passives_owned=False,
    )
    assert result == original


def test_defensive_stance_does_not_apply_without_shield():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Sword"))
    build.FrontBarSkills[0] = "Defensive Stance"

    original = GearCalculationInputs()
    result = OneHandShieldPassiveInputResolver().apply(
        original,
        build,
        active_bar="front",
        passives_owned=False,
    )
    assert result == original


def test_context_factory_uses_one_hand_shield_ownership_and_active_bar_equipment():
    build = _explicit_sword_and_shield()
    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="tank",
        build=build,
        progression=CharacterProgression(owned_skill_lines=("One Hand and Shield",)),
        active_bar="front",
    )

    assert context.core_state.derived[StatId.BLOCK_COST].final_value == 1120
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.60)
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1050
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1050


def test_context_factory_applies_defensive_stance_from_active_bar_slot():
    build = _explicit_sword_and_shield()
    build.FrontBarSkills[0] = "Defensive Stance"

    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="tank",
        build=build,
        progression=CharacterProgression(owned_skill_lines=("One Hand and Shield",)),
        active_bar="front",
    )

    assert context.core_state.derived[StatId.BLOCK_COST].final_value == 1008
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.65)
