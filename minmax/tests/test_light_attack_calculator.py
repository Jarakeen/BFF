import pytest

from minmax.combat_state import LightAttackState
from minmax.light_attack_calculator import (
    calculate_bow_light_attack,
    calculate_flame_staff_light_attack,
    calculate_frost_staff_light_attack,
    calculate_shock_staff_light_attack,
)
from minmax.formulas.additional_formulas import calculate_la_bow
from minmax.formulas.resolved_modifiers import (
    calculate_la_flame_staff,
    calculate_la_frost_staff,
    calculate_la_shock_staff,
)


def test_flame_staff_calculator_matches_formula():
    state = LightAttackState(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_la_damage=0.10,
        set_la_damage=0.05,
        flame_damage_done=0.05,
        direct_damage_done=0.05,
        single_target_damage_done=0.05,
        damage_done=0.05,
    )

    expected = calculate_la_flame_staff(
        magicka=state.magicka,
        stamina=state.stamina,
        la_flame_spell_damage=state.la_flame_spell_damage,
        la_flame_weapon_damage=state.la_flame_weapon_damage,
        skill2_la_damage=state.skill2_la_damage,
        cp_la_damage=state.cp_la_damage,
        skill_la_damage=state.skill_la_damage,
        set_la_damage=state.set_la_damage,
        flame_damage_done=state.flame_damage_done,
        direct_damage_done=state.direct_damage_done,
        single_target_damage_done=state.single_target_damage_done,
        damage_done=state.damage_done,
    )

    assert calculate_flame_staff_light_attack(state) == pytest.approx(expected)


def test_frost_staff_calculator_matches_formula():
    state = LightAttackState(
        magicka=30000,
        stamina=15000,
        la_frost_spell_damage=5000,
        la_frost_weapon_damage=4000,
    )

    expected = calculate_la_frost_staff(
        magicka=state.magicka,
        stamina=state.stamina,
        la_frost_spell_damage=state.la_frost_spell_damage,
        la_frost_weapon_damage=state.la_frost_weapon_damage,
    )

    assert calculate_frost_staff_light_attack(state) == pytest.approx(expected)


def test_shock_staff_calculator_matches_formula():
    state = LightAttackState(
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

    expected = calculate_la_shock_staff(
        magicka=state.magicka,
        stamina=state.stamina,
        la_shock_spell_damage=state.la_shock_spell_damage,
        la_shock_weapon_damage=state.la_shock_weapon_damage,
        skill2_la_damage=state.skill2_la_damage,
        cp_la_damage=state.cp_la_damage,
        skill_ha_damage=state.skill_ha_damage,
        set_ha_damage=state.set_ha_damage,
        buff_empower=state.buff_empower,
        shock_damage_done=state.shock_damage_done,
        single_target_damage_done=state.single_target_damage_done,
        dot_damage_done=state.dot_damage_done,
        damage_done=state.damage_done,
    )

    assert calculate_shock_staff_light_attack(state) == pytest.approx(expected)


def test_bow_calculator_matches_preserved_uesp_formula():
    state = LightAttackState(
        magicka=15000,
        stamina=30000,
        la_physical_spell_damage=4500,
        la_physical_weapon_damage=5000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_la_damage=0.10,
        set_la_damage=0.05,
        bow_damage_done=0.04,
        physical_damage_done=0.03,
        direct_damage_done=0.02,
        single_target_damage_done=0.01,
        damage_done=0.06,
        skill_line_damage_bow=0.07,
    )

    expected = calculate_la_bow(
        magicka=state.magicka,
        stamina=state.stamina,
        la_physical_weapon_damage=state.la_physical_weapon_damage,
        la_physical_spell_damage=state.la_physical_spell_damage,
        skill2_la_damage=state.skill2_la_damage,
        cp_la_damage=state.cp_la_damage,
        skill_la_damage=state.skill_la_damage,
        set_la_damage=state.set_la_damage,
        bow_damage_done=state.bow_damage_done,
        physical_damage_done=state.physical_damage_done,
        damage_done=state.damage_done,
        direct_damage_done=state.direct_damage_done,
        single_target_damage_done=state.single_target_damage_done,
        skill_line_damage_bow=state.skill_line_damage_bow,
    )

    assert calculate_bow_light_attack(state) == pytest.approx(expected)
