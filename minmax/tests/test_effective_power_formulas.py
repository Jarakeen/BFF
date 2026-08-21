"""Unit tests for minmax/formulas/effective_power.py.

Every expected value below is hand-calculated directly from the raw UESP
formulas in minmax/equations.py (that file is not touched/imported here --
it's plain text, not importable Python). See the docstring on each formula
function for the exact equation being verified. Expected results were
computed independently (same arithmetic, written out step by step in the
comments) rather than by calling the function under test.
"""

import pytest

from minmax.formulas.effective_power import (
    calculate_effective_power,
    calculate_effective_spell_power,
    calculate_effective_weapon_power,
)


def test_calculate_effective_spell_power():
    # magicka_power_term = round(30000 / 10.5) = round(2857.142857...) = 2857
    # base_power = 2857 + 5000 = 7857
    # critical_multiplier = 1 + 0.30*0.70 = 1.21
    # magic_damage_done_multiplier = 1 + 0.08 = 1.08
    # mitigation_multiplier = 1 - 0.20 = 0.80
    # target_damage_taken_multiplier = 1 + 0.05 = 1.05
    # damage_done_multiplier = 1 + 0.10 = 1.10
    # result = 7857 * 1.21 * 1.08 * 0.80 * 1.05 * 1.10 = 9487.195502400002
    result = calculate_effective_spell_power(
        magicka=30000,
        spell_damage=5000,
        spell_critical=0.30,
        attack_spell_critical_damage=0.70,
        cp_magic_damage_done=0.08,
        attack_spell_mitigation=0.20,
        target_damage_taken=0.05,
        damage_done=0.10,
    )
    assert result == pytest.approx(9487.195502400002)


def test_calculate_effective_spell_power_all_zero_inputs():
    # base_power = round(0/10.5) + 0 = 0, so the whole product is 0
    # regardless of the multiplier terms.
    result = calculate_effective_spell_power(
        magicka=0,
        spell_damage=0,
        spell_critical=0,
        attack_spell_critical_damage=0,
        cp_magic_damage_done=0,
        attack_spell_mitigation=0,
        target_damage_taken=0,
        damage_done=0,
    )
    assert result == pytest.approx(0.0)


def test_calculate_effective_weapon_power():
    # stamina_power_term = round(28000 / 10.5) = round(2666.666...) = 2667
    # base_power = 2667 + 4800 = 7467
    # critical_multiplier = 1 + 0.25*0.65 = 1.1625
    # physical_damage_done_multiplier = 1 + 0.06 = 1.06
    # mitigation_multiplier = 1 - 0.18 = 0.82
    # target_damage_taken_multiplier = 1 + 0.05 = 1.05
    # damage_done_multiplier = 1 + 0.10 = 1.10
    # result = 7467 * 1.1625 * 1.06 * 0.82 * 1.05 * 1.10 = 8714.466701325004
    result = calculate_effective_weapon_power(
        stamina=28000,
        weapon_damage=4800,
        weapon_critical=0.25,
        attack_weapon_critical_damage=0.65,
        cp_physical_damage_done=0.06,
        attack_physical_mitigation=0.18,
        target_damage_taken=0.05,
        damage_done=0.10,
    )
    assert result == pytest.approx(8714.466701325004)


def test_calculate_effective_power_picks_magicka_and_spell_side_when_larger():
    # Same inputs as the spell-power test above (magicka/spell side is the
    # larger side): the max() calls should all resolve to the spell values,
    # so the result must match calculate_effective_spell_power's result.
    result = calculate_effective_power(
        magicka=30000,
        stamina=28000,
        spell_damage=5000,
        weapon_damage=4800,
        spell_critical=0.30,
        weapon_critical=0.25,
        attack_spell_critical_damage=0.70,
        attack_weapon_critical_damage=0.65,
        cp_magic_damage_done=0.08,
        cp_physical_damage_done=0.06,
        attack_spell_mitigation=0.20,
        attack_physical_mitigation=0.18,
        target_damage_taken=0.05,
        damage_done=0.10,
    )
    assert result == pytest.approx(9487.195502400002)


def test_calculate_effective_power_picks_stamina_and_weapon_side_when_larger():
    # resource_power_term = round(max(20000, 32000) / 10.5) = round(3047.619...) = 3048
    # max_damage = max(4000, 6000) = 6000 -> base_power = 3048 + 6000 = 9048
    # max_critical_chance = max(0.20, 0.35) = 0.35
    # max_critical_damage = max(0.60, 0.75) = 0.75
    # critical_multiplier = 1 + 0.35*0.75 = 1.2625
    # max_damage_done_by_source = max(0.05, 0.09) = 0.09 -> multiplier = 1.09
    # max_mitigation = max(0.10, 0.22) = 0.22 -> multiplier = 0.78
    # target_damage_taken_multiplier = 1.05, damage_done_multiplier = 1.10
    # result = 9048 * 1.2625 * 1.09 * 0.78 * 1.05 * 1.10 = 11217.267161100004
    result = calculate_effective_power(
        magicka=20000,
        stamina=32000,
        spell_damage=4000,
        weapon_damage=6000,
        spell_critical=0.20,
        weapon_critical=0.35,
        attack_spell_critical_damage=0.60,
        attack_weapon_critical_damage=0.75,
        cp_magic_damage_done=0.05,
        cp_physical_damage_done=0.09,
        attack_spell_mitigation=0.10,
        attack_physical_mitigation=0.22,
        target_damage_taken=0.05,
        damage_done=0.10,
    )
    assert result == pytest.approx(11217.267161100004)


def test_calculate_effective_power_mixes_sides_independently():
    # Regression guard for a subtle UESP detail: each max() term is
    # evaluated independently -- EffectivePower does NOT simply pick "the
    # better overall side" once and stick with it. Here spell_critical is
    # the larger crit chance (0.5 vs 0.1), but attack_weapon_critical_damage
    # is the larger crit-damage multiplier (0.9 vs 0.2), so the crit term
    # must combine max(0.5, 0.1) * max(0.2, 0.9) = 0.5 * 0.9 = 0.45,
    # not either side's own (chance * damage) product taken as a pair.
    resource_power_term = round(max(10000, 10000) / 10.5)
    base_power = resource_power_term + max(1000, 1000)
    critical_multiplier = 1 + max(0.5, 0.1) * max(0.2, 0.9)
    dd_multiplier = 1 + max(0.0, 0.0)
    mitigation_multiplier = 1 - max(0.0, 0.0)
    expected = base_power * critical_multiplier * dd_multiplier * mitigation_multiplier * 1 * 1

    result = calculate_effective_power(
        magicka=10000,
        stamina=10000,
        spell_damage=1000,
        weapon_damage=1000,
        spell_critical=0.5,
        weapon_critical=0.1,
        attack_spell_critical_damage=0.2,
        attack_weapon_critical_damage=0.9,
        cp_magic_damage_done=0.0,
        cp_physical_damage_done=0.0,
        attack_spell_mitigation=0.0,
        attack_physical_mitigation=0.0,
        target_damage_taken=0.0,
        damage_done=0.0,
    )
    assert result == pytest.approx(expected)
    assert critical_multiplier == pytest.approx(1.45)
