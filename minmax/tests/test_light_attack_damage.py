import pytest

from old_pages.old_light_attack_damage import (
    calculate_la_flame_staff,
    calculate_la_frost_staff,
    calculate_la_shock_staff,
)


def test_calculate_la_flame_staff():
    result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
    )

    expected = (
        min(
            int(0.045 * 30000)
            + int(0.4725 * 5000),
            3465,
        )
    )

    assert result == pytest.approx(expected)


def test_calculate_la_frost_staff():
    result = calculate_la_frost_staff(
        magicka=30000,
        stamina=15000,
        la_frost_spell_damage=5000,
        la_frost_weapon_damage=4000,
    )

    expected = (
        min(
            int(0.045 * 30000)
            + int(0.4725 * 5000),
            3465,
        )
    )

    assert result == pytest.approx(expected)


def test_calculate_la_flame_staff_applies_modifiers():
    base = min(
        int(0.045 * 30000)
        + int(0.4725 * 5000),
        3465,
    )

    result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_la_damage=0.10,
        set_la_damage=0.05,
        flame_damage_done=0.10,
        direct_damage_done=0.05,
        single_target_damage_done=0.05,
        damage_done=0.05,
    )

    # Flame
    expected = (base + 100) * 1.45
    assert result == pytest.approx(expected)

    assert result == pytest.approx(expected)


def test_la_staff_uses_higher_spell_or_weapon_damage():
    spell_result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=6000,
        la_flame_weapon_damage=4000,
    )

    weapon_result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=4000,
        la_flame_weapon_damage=6000,
    )

    assert spell_result == pytest.approx(weapon_result)


def test_la_staff_cap_is_3465():
    result = calculate_la_flame_staff(
        magicka=100000,
        stamina=100000,
        la_flame_spell_damage=100000,
        la_flame_weapon_damage=100000,
    )

    assert result == pytest.approx(3465)


def test_calculate_la_shock_staff_preserves_source_modifiers():
    base = min(
        int(0.045 * 30000)
        + int(0.4725 * 5000),
        3465,
    )

    result = calculate_la_shock_staff(
        magicka=30000,
        stamina=15000,
        la_shock_spell_damage=5000,
        la_shock_weapon_damage=4000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_ha_damage=0.10,
        set_ha_damage=0.05,
        buff_empower=0.10,
        shock_damage_done=0.05,
        single_target_damage_done=0.05,
        dot_damage_done=0.05,
        damage_done=0.05,
    )

    # Shock
    expected = (base + 100) * 1.50
    assert result == pytest.approx(expected)

    assert result == pytest.approx(expected)