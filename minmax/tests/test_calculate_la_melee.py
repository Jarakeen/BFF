import pytest

from minmax.formulas.calculate_la_melee import calculate_la_melee


def test_calculate_la_melee():
    result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
    )

    expected = min(
        int(0.05 * 30000)
        + int(0.550 * 5000),
        3850,
    )

    assert result == pytest.approx(expected)


def test_calculate_la_melee_uses_higher_physical_damage_source():
    weapon_result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=6000,
        la_physical_spell_damage=4000,
    )

    spell_result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=4000,
        la_physical_spell_damage=6000,
    )

    assert weapon_result == pytest.approx(spell_result)


def test_calculate_la_melee_applies_skill2_damage():
    result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
        skill2_la_damage=100,
    )

    base = min(
        int(0.05 * 30000)
        + int(0.550 * 5000),
        3850,
    )

    assert result == pytest.approx(base + 100)


def test_calculate_la_melee_applies_modifiers():
    base = min(
        int(0.05 * 30000)
        + int(0.550 * 5000),
        3850,
    )

    result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_la_damage=0.10,
        set_la_damage=0.05,
        set_la_melee_damage=0.10,
        physical_damage_done=0.05,
        damage_done=0.05,
        direct_damage_done=0.05,
        single_target_damage_done=0.05,
    )

    expected = (base + 100) * 1.50

    assert result == pytest.approx(expected)


def test_calculate_la_melee_has_3850_base_cap():
    result = calculate_la_melee(
        magicka=100000,
        stamina=100000,
        la_physical_weapon_damage=100000,
        la_physical_spell_damage=100000,
    )

    assert result == pytest.approx(3850)


def test_calculate_la_melee_uses_max_magicka_or_stamina():
    magicka_result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
    )

    stamina_result = calculate_la_melee(
        magicka=15000,
        stamina=30000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
    )

    assert magicka_result == pytest.approx(stamina_result)


def test_calculate_la_melee_zero_inputs():
    result = calculate_la_melee(
        magicka=0,
        stamina=0,
        la_physical_weapon_damage=0,
        la_physical_spell_damage=0,
    )

    assert result == pytest.approx(0)


def test_calculate_la_melee_modifier_sources_are_independent():
    base = min(
        int(0.05 * 30000)
        + int(0.550 * 5000),
        3850,
    )

    result = calculate_la_melee(
        magicka=30000,
        stamina=15000,
        la_physical_weapon_damage=5000,
        la_physical_spell_damage=4000,
        cp_la_damage=0.10,
        skill_la_damage=0.20,
        set_la_damage=0.30,
        set_la_melee_damage=0.40,
        physical_damage_done=0.50,
        damage_done=0.60,
        direct_damage_done=0.70,
        single_target_damage_done=0.80,
    )

    expected = base * 4.60

    assert result == pytest.approx(expected)