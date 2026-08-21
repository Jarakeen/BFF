import pytest

from old_pages.old_combat_costs import (
    calculate_bash_cost,
    calculate_bash_damage,
    calculate_block_cost,
    calculate_break_free_cost,
    calculate_damage_shield,
    calculate_damage_shield_cost,
    calculate_fear_duration,
    calculate_roll_dodge_cost,
)


def test_calculate_bash_cost():
    assert calculate_bash_cost() == pytest.approx(765)


def test_calculate_bash_cost_applies_modifiers():
    result = calculate_bash_cost(
        item_bash_cost=100,
        cp_bash_cost=0.10,
        skill_bash_cost=0.20,
        set_bash_cost=0.30,
    )

    expected = 865 * 1.10 * 1.20 * 1.30

    assert result == pytest.approx(expected)


def test_calculate_bash_damage():
    result = calculate_bash_damage(
        spell_resist=1000,
        physical_resist=2000,
    )

    expected = 2000 * 0.011250 + 1

    assert result == pytest.approx(expected)


def test_calculate_bash_damage_uses_max_resistance():
    spell_result = calculate_bash_damage(
        spell_resist=3000,
        physical_resist=1000,
    )

    physical_result = calculate_bash_damage(
        spell_resist=1000,
        physical_resist=3000,
    )

    assert spell_result == pytest.approx(physical_result)


def test_calculate_bash_damage_applies_modifiers_and_flat_bonuses():
    result = calculate_bash_damage(
        spell_resist=1000,
        physical_resist=2000,
        cp_bash_damage=0.05,
        skill2_bash_damage=0.10,
        physical_damage_done=0.05,
        damage_done=0.05,
        direct_damage_done=0.05,
        single_target_damage_done=0.05,
        skill_bash_damage=0.10,
        set_extra_bash_damage=50,
        skill_extra_bash_damage=25,
        item_extra_bash_damage=25,
    )

    base = (
        2000 * 0.011250
        + 1
        + 0.05
        + 0.10
    )

    expected = (
        base
        * (
            1
            + 0.05
            + 0.05
            + 0.05
            + 0.05
            + 0.10
        )
        + 50
        + 25
        + 25
    )

    assert result == pytest.approx(expected)


def test_calculate_block_cost():
    assert calculate_block_cost() == pytest.approx(1750)


def test_calculate_block_cost_applies_sturdy_and_modifiers():
    result = calculate_block_cost(
        item_block_cost=100,
        item_sturdy=0.20,
        cp_block_cost=0.10,
        set_block_cost=0.05,
        skill_block_cost=0.05,
        buff_block_cost=0.10,
        skill2_block_cost=0.05,
    )

    expected = (
        1850
        * 0.80
        * 1.10
        * 1.05
        * 1.05
        * 1.10
        * 1.05
    )

    assert result == pytest.approx(expected)


def test_calculate_roll_dodge_cost():
    assert calculate_roll_dodge_cost() == pytest.approx(4040)


def test_calculate_roll_dodge_cost_applies_modifiers():
    result = calculate_roll_dodge_cost(
        skill2_roll_dodge_cost=100,
        cp_roll_dodge_cost=0.10,
        skill_roll_dodge_cost=0.05,
        item_roll_dodge_cost=0.05,
        set_roll_dodge_cost=0.10,
        buff_roll_dodge_cost=0.05,
    )

    expected = (
        (4040 + 100)
        * 1.10
        * (1 + 0.05 + 0.05 + 0.10 + 0.05)
    )

    assert result == pytest.approx(expected)


def test_calculate_break_free_cost():
    assert calculate_break_free_cost() == pytest.approx(5400)


def test_calculate_break_free_cost_applies_modifiers():
    result = calculate_break_free_cost(
        skill2_break_free_cost=100,
        cp_break_free_cost=0.10,
        skill_break_free_cost=0.05,
        buff_break_free_cost=0.05,
        item_break_free_cost=0.10,
        set_break_free_cost=0.05,
    )

    expected = (
        (5400 + 100)
        * 1.10
        * (1 + 0.05 + 0.05 + 0.10 + 0.05)
    )

    assert result == pytest.approx(expected)


def test_calculate_fear_duration():
    assert calculate_fear_duration() == pytest.approx(4)


def test_calculate_fear_duration_applies_modifiers():
    result = calculate_fear_duration(
        cp_fear_duration=0.10,
        set_crowd_control_duration=0.20,
    )

    assert result == pytest.approx(4 * 1.10 * 1.20)


def test_calculate_damage_shield():
    assert calculate_damage_shield() == pytest.approx(0)


def test_calculate_damage_shield_applies_modifiers():
    result = calculate_damage_shield(
        cp_damage_shield=0.10,
        buff_damage_shield=0.20,
        set_damage_shield=0.30,
        skill_damage_shield=0.40,
    )

    expected = (
        1.10
        * 1.20
        * 1.30
        * 1.40
        - 1
    )

    assert result == pytest.approx(expected)


def test_calculate_damage_shield_cost():
    assert calculate_damage_shield_cost(
        cp_damage_shield_cost=100,
        skill_damage_shield_cost=50,
    ) == pytest.approx(150)


def test_zero_inputs_produce_expected_baselines():
    assert calculate_damage_shield_cost() == pytest.approx(0)
    