from math import floor
import pytest
from minmax.formulas.math_utils import fround
from minmax.formulas.status_damage import (
    calculate_burning_damage,
    calculate_chilled_damage,
    calculate_concussion_damage,
    calculate_status_spell_damage,
)


def test_calculate_status_spell_damage():
    assert calculate_status_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage=500,
        buff_spell_damage=0.10,
        skill_spell_damage=0.05,
    ) == pytest.approx(3000 + 500 * 1.15)


def test_calculate_status_spell_damage_all_zero_bonus():
    assert calculate_status_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage=500,
    ) == pytest.approx(3500)


def test_calculate_burning_damage():
    result = calculate_burning_damage(
        magicka=30000,
        stamina=15000,
        status_flame_spell_damage=5000,
        status_flame_weapon_damage=4000,
    )

    expected = (
        int(0.01600000075995922 * 30000)
        + int(0.1679999977350235 * 5000)
    )

    assert result == pytest.approx(expected)


def test_calculate_burning_damage_uses_stamina_when_higher():
    result = calculate_burning_damage(
        magicka=10000,
        stamina=30000,
        status_flame_spell_damage=5000,
        status_flame_weapon_damage=4000,
    )

    expected = (
        int(0.01600000075995922 * 30000)
        + int(0.1679999977350235 * 5000)
    )

    assert result == pytest.approx(expected)


def test_calculate_burning_damage_uses_weapon_damage_when_higher():
    result = calculate_burning_damage(
        magicka=30000,
        stamina=15000,
        status_flame_spell_damage=4000,
        status_flame_weapon_damage=5000,
    )

    expected = (
        int(0.01600000075995922 * 30000)
        + int(0.1679999977350235 * 5000)
    )

    assert result == pytest.approx(expected)


def test_calculate_burning_damage_applies_modifiers():
    base = (
        int(0.01600000075995922 * 30000)
        + int(0.1679999977350235 * 5000)
    )

    result = calculate_burning_damage(
        magicka=30000,
        stamina=15000,
        status_flame_spell_damage=5000,
        status_flame_weapon_damage=4000,
        burning_damage=0.10,
        flame_damage_done=0.05,
        dot_damage_done=0.10,
        single_target_damage_done=0.05,
        damage_done=0.10,
    )

    assert result == pytest.approx(base * 1.40)


def test_calculate_chilled_damage():
    base = (
        floor(fround(0.008) * 30000)
        + floor(fround(0.084) * 5000)
    )

    result = calculate_chilled_damage(
        magicka=30000,
        stamina=15000,
        status_frost_spell_damage=5000,
        status_frost_weapon_damage=4000,
    )

    assert result == pytest.approx(base)


def test_calculate_concussion_damage():
    base = (
        floor(fround(0.008) * 30000)
        + floor(fround(0.084) * 5000)
    )

    result = calculate_concussion_damage(
        magicka=30000,
        stamina=15000,
        status_shock_spell_damage=5000,
        status_shock_weapon_damage=4000,
    )

    assert result == pytest.approx(base)


def test_calculate_chilled_damage_applies_modifiers():
    # UESP:
    # floor(fround(0.008) * 30000) = 240
    # floor(fround(0.084) * 5000) = 419
    # total = 659
    base = 659

    result = calculate_chilled_damage(
        magicka=30000,
        stamina=15000,
        status_frost_spell_damage=5000,
        status_frost_weapon_damage=4000,
        frost_damage_done=0.10,
        direct_damage_done=0.05,
        single_target_damage_done=0.10,
        damage_done=0.05,
    )

    assert result == pytest.approx(base * 1.30)


def test_calculate_concussion_damage_applies_modifiers():
    # UESP:
    # floor(fround(0.008) * 30000) = 240
    # floor(fround(0.084) * 5000) = 419
    # total = 659
    base = 659

    result = calculate_concussion_damage(
        magicka=30000,
        stamina=15000,
        status_shock_spell_damage=5000,
        status_shock_weapon_damage=4000,
        shock_damage_done=0.10,
        direct_damage_done=0.05,
        single_target_damage_done=0.10,
        damage_done=0.05,
    )

    assert result == pytest.approx(base * 1.30)


def test_status_damage_zero_inputs():
    assert calculate_status_spell_damage(
        spell_damage=0,
        skill_bonus_spell_damage=0,
    ) == 0

    assert calculate_burning_damage(
        magicka=0,
        stamina=0,
        status_flame_spell_damage=0,
        status_flame_weapon_damage=0,
    ) == 0

    assert calculate_chilled_damage(
        magicka=0,
        stamina=0,
        status_frost_spell_damage=0,
        status_frost_weapon_damage=0,
    ) == 0

    assert calculate_concussion_damage(
        magicka=0,
        stamina=0,
        status_shock_spell_damage=0,
        status_shock_weapon_damage=0,
    ) == 0