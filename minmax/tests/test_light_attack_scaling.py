import math
import pytest

from minmax.formulas.light_attack_scaling import (
    calculate_la_flame_spell_damage,
    calculate_la_shock_weapon_damage,
    calculate_la_frost_spell_damage,
    calculate_la_flame_weapon_damage,
    calculate_la_frost_weapon_damage,
    calculate_la_magic_spell_damage,
    calculate_la_physical_weapon_damage,
    calculate_la_shock_spell_damage,
)

def test_calculate_la_flame_spell_damage():
    assert calculate_la_flame_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage_flame=500,
    ) == pytest.approx(3500)


def test_calculate_la_flame_spell_damage_with_modifiers():
    assert calculate_la_flame_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage_flame=500,
        skill2_la_spell_damage=100,
        buff_spell_damage=0.10,
        skill_spell_damage=0.05,
    ) == pytest.approx(
        3000 + 600 * 1.15
    )


def test_calculate_la_flame_weapon_damage_with_modifiers():
    assert calculate_la_flame_weapon_damage(
        weapon_damage=3000,
        skill_bonus_weapon_damage_flame=500,
        skill2_la_weapon_damage=100,
        buff_weapon_damage=0.10,
        skill_weapon_damage=0.05,
    ) == pytest.approx(
        3000 + 600 * 1.15
    )


def test_calculate_la_shock_spell_damage_includes_channel_bonus():
    assert calculate_la_shock_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage_shock=500,
        skill2_la_spell_damage=100,
        item_channel_spell_damage=50,
    ) == pytest.approx(3650)

    def test_calculate_la_shock_weapon_damage_includes_channel_bonus():
        assert calculate_la_shock_weapon_damage(
            weapon_damage=3000,
            skill_bonus_weapon_damage_shock=500,
            skill2_la_weapon_damage=100,
            item_channel_weapon_damage=50,
        ) == pytest.approx(3650)


def test_calculate_la_frost_spell_damage():
    assert calculate_la_frost_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage_frost=500,
        skill2_la_spell_damage=100,
        buff_spell_damage=0.10,
        skill_spell_damage=0.05,
    ) == pytest.approx(3000 + 600 * 1.15)


def test_calculate_la_frost_weapon_damage():
    assert calculate_la_frost_weapon_damage(
        weapon_damage=3000,
        skill_bonus_weapon_damage_frost=500,
        skill2_la_weapon_damage=100,
        buff_weapon_damage=0.10,
        skill_weapon_damage=0.05,
    ) == pytest.approx(3000 + 600 * 1.15)


def test_calculate_la_magic_spell_damage_includes_channel_bonus():
    assert calculate_la_magic_spell_damage(
        spell_damage=3000,
        skill_bonus_spell_damage_magic=500,
        skill2_la_spell_damage=100,
        item_channel_spell_damage=50,
    ) == pytest.approx(3650)


def test_calculate_la_physical_weapon_damage():
    assert calculate_la_physical_weapon_damage(
        weapon_damage=3000,
        skill_bonus_weapon_damage_physical=500,
        skill2_la_weapon_damage=100,
        buff_weapon_damage=0.10,
        skill_weapon_damage=0.05,
    ) == pytest.approx(3000 + 600 * 1.15)