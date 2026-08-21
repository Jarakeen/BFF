import pytest

from minmax.formulas.item_effects import (
    calculate_bloodthirsty_spell_damage,
    calculate_bloodthirsty_weapon_damage,
    calculate_potion_cooldown,
    calculate_potion_duration,
    calculate_sneak_cost,
    calculate_ultimate_restore,
)


def test_calculate_bloodthirsty_spell_damage():
    result = calculate_bloodthirsty_spell_damage(
        target_percent_health=0.45,
        item_bloodthirsty=0.15,
    )

    expected = (
        1 - (0.45 / 0.9)
    ) * 0.15

    assert result == pytest.approx(expected)


def test_calculate_bloodthirsty_weapon_damage():
    result = calculate_bloodthirsty_weapon_damage(
        target_percent_health=0.45,
        item_bloodthirsty=0.15,
    )

    expected = (
        1 - (0.45 / 0.9)
    ) * 0.15

    assert result == pytest.approx(expected)


def test_bloodthirsty_caps_target_health_at_90_percent():
    result = calculate_bloodthirsty_spell_damage(
        target_percent_health=1.0,
        item_bloodthirsty=0.15,
    )

    assert result == pytest.approx(0.0)


def test_bloodthirsty_at_zero_health():
    result = calculate_bloodthirsty_weapon_damage(
        target_percent_health=0.0,
        item_bloodthirsty=0.15,
    )

    assert result == pytest.approx(0.15)


def test_calculate_ultimate_restore():
    assert calculate_ultimate_restore(
        item_ultimate_restore=10,
        set_ultimate_restore=15,
    ) == pytest.approx(25)


def test_calculate_potion_duration():
    assert calculate_potion_duration(
        item_potion_duration=2,
        skill_potion_duration=3,
    ) == pytest.approx(5)


def test_calculate_potion_cooldown():
    assert calculate_potion_cooldown(
        item_potion_duration=2,
        skill_potion_duration=3,
        set_potion_duration=4,
    ) == pytest.approx(9)


def test_calculate_sneak_cost():
    assert calculate_sneak_cost() == pytest.approx(133)


def test_calculate_sneak_cost_applies_all_modifiers():
    result = calculate_sneak_cost(
        cp_sneak_cost=0.10,
        skill_sneak_cost=0.20,
        item_sneak_cost=0.30,
        set_sneak_cost=0.40,
        buff_sneak_cost=0.50,
    )

    expected = (
        133
        * 1.10
        * 1.20
        * 1.30
        * 1.40
        * 1.50
    )

    assert result == pytest.approx(expected)