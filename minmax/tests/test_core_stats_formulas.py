"""Unit tests for services/minmax/formulas/core_stats.py.

Every expected value below is hand-calculated directly from the raw UESP
formulas in services/minmax/equations.py (that file is not touched/imported
here -- it's plain text, not importable Python). See the docstring on each
formula function for the exact equation being verified.
"""

import math

import pytest

from minmax.formulas.core_stats import (
    calculate_health_recovery,
    calculate_magicka_recovery,
    calculate_max_health,
    calculate_max_magicka,
    calculate_max_stamina,
    calculate_physical_penetration,
    calculate_physical_resistance,
    calculate_spell_critical,
    calculate_spell_critical_damage,
    calculate_spell_critical_healing,
    calculate_spell_damage,
    calculate_spell_penetration,
    calculate_spell_resistance,
    calculate_stamina_recovery,
    calculate_weapon_critical_damage,
    calculate_weapon_critical_healing,
    calculate_weapon_damage,
)


def test_calculate_max_health():
    # Health = (300*50 + 1000 + 122*0 + 1000 + 500 + 2000 + 0 + 2000) * (1 + 0.05 + 0.10)
    # = 21500 * 1.15 = 24725.0
    result = calculate_max_health(
        level=50,
        attribute_health=0,
        item_health=1000,
        set_health=500,
        food_health=2000,
        skill2_health=0,
        mundus_health=2000,
        skill_health=0.05,
        buff_health=0.10,
    )
    assert result == pytest.approx(24725.0)


def test_calculate_max_magicka():
    # Magicka = (220*50 + 1000 + 111*64 + 1000 + 500 + 1500 + 2000 + 0) * (1 + 0.05 + 0.10)
    # = 24104 * 1.15 = 27719.6
    result = calculate_max_magicka(
        level=50,
        attribute_magicka=64,
        item_magicka=1000,
        set_magicka=500,
        food_magicka=1500,
        mundus_magicka=2000,
        skill2_magicka=0,
        skill_magicka=0.05,
        buff_magicka=0.10,
    )
    assert result == pytest.approx(27719.6)


def test_calculate_max_stamina():
    # Stamina = (220*50 + 1000 + 111*64 + 1200 + 500 + 1500 + 2000 + 0) * (1 + 0.05 + 0.10)
    # = 24304 * 1.15 = 27949.6
    result = calculate_max_stamina(
        level=50,
        attribute_stamina=64,
        item_stamina=1200,
        set_stamina=500,
        food_stamina=1500,
        mundus_stamina=2000,
        skill2_stamina=0,
        skill_stamina=0.05,
        buff_stamina=0.10,
    )
    assert result == pytest.approx(27949.6)


def test_calculate_health_recovery():
    # base_level_regen = round(5.592*50 + 29.4) = round(309.0) = 309
    # resist_bonus = min(1320, floor(0.03 * (18000 + 18000))) = min(1320, 1080) = 1080
    # food_term = 300 * (1 / (1 + 0)) = 300
    # base = 309 + 100 + 200 + 1080 + 0 + 300 = 1989
    # result = 1989 * (1 + 0.1 + 0.05 + 0.05) * (1 + 0) * (1 + 0) = 1989 * 1.2 = 2386.8
    result = calculate_health_recovery(
        level=50,
        item_health_regen=100,
        set_health_regen=200,
        set_health_regen_resist_factor=0.03,
        physical_resistance=18000,
        spell_resistance=18000,
        mundus_health_regen=0,
        food_health_regen=300,
        skill2_health_regen=0,
        cp_health_regen=0.1,
        skill_health_regen=0.05,
        buff_health_regen=0.05,
        vampire_health_regen=0,
    )
    assert result == pytest.approx(2386.8)


def test_calculate_health_recovery_resist_bonus_is_capped_at_1320():
    # resist term uncapped would be floor(1 * 100000) = 100000, but capped to 1320
    base_level_regen = round(5.592 * 10 + 29.4)
    expected_base = base_level_regen + 0 + 0 + 1320 + 0 + 0
    expected = expected_base * 1.0 * 1.0 * 1.0

    result = calculate_health_recovery(
        level=10,
        item_health_regen=0,
        set_health_regen=0,
        set_health_regen_resist_factor=1,
        physical_resistance=50000,
        spell_resistance=50000,
        mundus_health_regen=0,
        food_health_regen=0,
        skill2_health_regen=0,
        cp_health_regen=0,
        skill_health_regen=0,
        buff_health_regen=0,
        vampire_health_regen=0,
    )
    assert result == pytest.approx(expected)


def test_calculate_magicka_recovery():
    # base_level_regen = round(9.30612*50 + 48.7) = round(514.006) = 514
    # food_term = 300 * (1/(1+0)) = 300
    # base = 514 + 100 + 200 + 0 + 300 = 1114
    # result = 1114 * (1 + 0.1 + 0.05 + 0.05) * (1 + 0) = 1114 * 1.2 = 1336.8
    result = calculate_magicka_recovery(
        level=50,
        item_magicka_regen=100,
        set_magicka_regen=200,
        mundus_magicka_regen=0,
        food_magicka_regen=300,
        skill2_magicka_regen=0,
        cp_magicka_regen=0.1,
        skill_magicka_regen=0.05,
        buff_magicka_regen=0.05,
    )
    assert result == pytest.approx(1336.8)


def test_calculate_stamina_recovery():
    # base_level_regen = round(9.30612*50 + 48.7) = 514
    # food_term = 350
    # base = 514 + 150 + 250 + 0 + 350 = 1264
    # result = 1264 * 1.2 = 1516.8
    result = calculate_stamina_recovery(
        level=50,
        item_stamina_regen=150,
        set_stamina_regen=250,
        mundus_stamina_regen=0,
        food_stamina_regen=350,
        skill2_stamina_regen=0,
        cp_stamina_regen=0.1,
        skill_stamina_regen=0.05,
        buff_stamina_regen=0.05,
    )
    assert result == pytest.approx(1516.8)


def test_calculate_spell_damage():
    # base = 20*50 + 1000 + 500 + 0 + 0 + 200 = 2700
    # result = 2700 * (1 + 0.10 + 0.05) + 150 = 3105.0 + 150 = 3255.0
    result = calculate_spell_damage(
        level=50,
        item_spell_damage=1000,
        set_spell_damage=500,
        skill2_spell_damage=0,
        mundus_spell_damage=0,
        cp_spell_damage=200,
        skill_spell_damage=0.10,
        buff_spell_damage=0.05,
        bloodthirsty_spell_damage=150,
    )
    assert result == pytest.approx(3255.0)


def test_calculate_spell_damage_bloodthirsty_is_additive_not_scaled():
    without_bloodthirsty = calculate_spell_damage(
        level=50,
        item_spell_damage=1000,
        set_spell_damage=500,
        skill2_spell_damage=0,
        mundus_spell_damage=0,
        cp_spell_damage=200,
        skill_spell_damage=0.10,
        buff_spell_damage=0.05,
        bloodthirsty_spell_damage=0,
    )
    with_bloodthirsty = calculate_spell_damage(
        level=50,
        item_spell_damage=1000,
        set_spell_damage=500,
        skill2_spell_damage=0,
        mundus_spell_damage=0,
        cp_spell_damage=200,
        skill_spell_damage=0.10,
        buff_spell_damage=0.05,
        bloodthirsty_spell_damage=150,
    )
    # Bloodthirsty is added AFTER the percent multiplier, not before.
    assert with_bloodthirsty - without_bloodthirsty == pytest.approx(150.0)


def test_calculate_weapon_damage():
    # base = 20*50 + 900 + 400 + 0 + 0 + 180 = 2480
    # result = 2480 * (1 + 0.10 + 0.05) + 100 = 2852.0 + 100 = 2952.0
    result = calculate_weapon_damage(
        level=50,
        item_weapon_damage=900,
        set_weapon_damage=400,
        skill2_weapon_damage=0,
        mundus_weapon_damage=0,
        cp_weapon_damage=180,
        skill_weapon_damage=0.10,
        buff_weapon_damage=0.05,
        bloodthirsty_weapon_damage=100,
    )
    assert result == pytest.approx(2952.0)


def test_calculate_spell_critical():
    # critical_rating = 500 + 0 + 300 + 1000 + 0 = 1800
    # factor = 1 / (2*160*(100+160)) = 1 / 83200
    # result = 1800/83200 + 0.10 + 0.05 + 0.03
    critical_rating = 1800
    factor = 1 / (2 * 160 * (100 + 160))
    expected = critical_rating * factor + 0.10 + 0.05 + 0.03

    result = calculate_spell_critical(
        set_spell_critical=500,
        skill2_spell_critical=0,
        buff_spell_critical=300,
        cp_spell_critical=1000,
        mundus_spell_critical=0,
        effective_level=160,
        item_spell_critical=0.05,
        skill_spell_critical=0.03,
    )
    assert result == pytest.approx(expected)


def test_calculate_spell_critical_damage():
    # sum = 0.10 + 0.05 + 0.05 + 0 + 0.12 + 0 + 0.08 + 0.5 = 0.90
    # result = 0.90 * (1 + 0.10) = 0.99
    result = calculate_spell_critical_damage(
        cp_spell_critical_damage=0.10,
        skill_critical_damage=0.05,
        cp_critical_damage=0.05,
        mundus_critical_damage=0,
        set_critical_damage=0.12,
        item_critical_damage=0,
        buff_critical_damage=0.08,
        skill2_critical_damage=0.10,
    )
    assert result == pytest.approx(0.99)


def test_calculate_weapon_critical_damage():
    # sum = 0.09 + 0.05 + 0.05 + 0 + 0.12 + 0 + 0.08 + 0.5 = 0.89
    # result = 0.89 * 1.10 = 0.979
    result = calculate_weapon_critical_damage(
        cp_weapon_critical_damage=0.09,
        skill_critical_damage=0.05,
        cp_critical_damage=0.05,
        mundus_critical_damage=0,
        set_critical_damage=0.12,
        item_critical_damage=0,
        buff_critical_damage=0.08,
        skill2_critical_damage=0.10,
    )
    assert result == pytest.approx(0.979)


def test_calculate_spell_critical_healing():
    # sum = 0.10 + 0.05 + 0.05 + 0 + 0.10 + 0 + 0.05 + 0.5 = 0.85
    # result = 0.85 * 1.10 = 0.935
    result = calculate_spell_critical_healing(
        cp_spell_critical_healing=0.10,
        skill_critical_healing=0.05,
        cp_critical_healing=0.05,
        mundus_critical_healing=0,
        set_critical_healing=0.10,
        item_critical_healing=0,
        buff_critical_healing=0.05,
        skill2_critical_healing=0.10,
    )
    assert result == pytest.approx(0.935)


def test_calculate_weapon_critical_healing():
    # sum = 0.09 + 0.05 + 0.05 + 0 + 0.10 + 0 + 0.05 + 0.5 = 0.84
    # result = 0.84 * 1.10 = 0.924
    result = calculate_weapon_critical_healing(
        cp_weapon_critical_healing=0.09,
        skill_critical_healing=0.05,
        cp_critical_healing=0.05,
        mundus_critical_healing=0,
        set_critical_healing=0.10,
        item_critical_healing=0,
        buff_critical_healing=0.05,
        skill2_critical_healing=0.10,
    )
    assert result == pytest.approx(0.924)


def test_calculate_spell_resistance():
    # base = 1000 + 0 + 0 + 500 + 0 + 2000 = 3500
    # result = 3500 * 1.10 = 3850.0
    result = calculate_spell_resistance(
        item_spell_resist=1000,
        skill2_spell_resist=0,
        mundus_spell_resist=0,
        set_spell_resist=500,
        skill_spell_resist=0,
        cp_spell_resist=2000,
        buff_spell_resist=0.10,
    )
    assert result == pytest.approx(3850.0)


def test_calculate_physical_resistance():
    # base = 1200 + 0 + 0 + 600 + 0 + 2000 = 3800
    # result = 3800 * 1.10 = 4180.0
    result = calculate_physical_resistance(
        item_physical_resist=1200,
        skill2_physical_resist=0,
        mundus_physical_resist=0,
        set_physical_resist=600,
        skill_physical_resist=0,
        cp_physical_resist=2000,
        buff_physical_resist=0.10,
    )
    assert result == pytest.approx(4180.0)


def test_calculate_spell_penetration():
    # sum = 2000 + 1000 + 0 + 2900 + 0 + 0 = 5900
    result = calculate_spell_penetration(
        item_spell_penetration=2000,
        set_spell_penetration=1000,
        skill_spell_penetration=0,
        cp_spell_penetration=2900,
        buff_spell_penetration=0,
        mundus_spell_penetration=0,
    )
    assert result == pytest.approx(5900)


def test_calculate_physical_penetration():
    # sum = 1800 + 1000 + 0 + 2900 + 0 + 0 = 5700
    result = calculate_physical_penetration(
        item_physical_penetration=1800,
        set_physical_penetration=1000,
        skill_physical_penetration=0,
        cp_physical_penetration=2900,
        buff_physical_penetration=0,
        mundus_physical_penetration=0,
    )
    assert result == pytest.approx(5700)


def test_all_zero_inputs_produce_baseline_values_not_errors():
    # Sanity check: zeroed inputs should not raise and should match the
    # formula's "floor" constants (e.g. the flat 1000 Magicka base, the 0.10
    # base spell crit chance, etc.) rather than silently defaulting/assuming
    # anything not in the formula.
    assert calculate_max_magicka(
        level=0,
        attribute_magicka=0,
        item_magicka=0,
        set_magicka=0,
        food_magicka=0,
        mundus_magicka=0,
        skill2_magicka=0,
        skill_magicka=0,
        buff_magicka=0,
    ) == pytest.approx(1000.0)

    assert calculate_spell_critical(
        set_spell_critical=0,
        skill2_spell_critical=0,
        buff_spell_critical=0,
        cp_spell_critical=0,
        mundus_spell_critical=0,
        effective_level=160,
        item_spell_critical=0,
        skill_spell_critical=0,
    ) == pytest.approx(0.10)

    assert calculate_spell_penetration(
        item_spell_penetration=0,
        set_spell_penetration=0,
        skill_spell_penetration=0,
        cp_spell_penetration=0,
        buff_spell_penetration=0,
        mundus_spell_penetration=0,
    ) == 0