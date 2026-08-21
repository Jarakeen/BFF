from __future__ import annotations

from minmax.combat_state import LightAttackState
from minmax.formulas.resolved_modifiers import (
    calculate_la_flame_staff,
    calculate_la_frost_staff,
    calculate_la_shock_staff,
)


def calculate_flame_staff_light_attack(
    state: LightAttackState,
) -> float:
    return calculate_la_flame_staff(
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


def calculate_frost_staff_light_attack(
    state: LightAttackState,
) -> float:
    return calculate_la_frost_staff(
        magicka=state.magicka,
        stamina=state.stamina,
        la_frost_spell_damage=state.la_frost_spell_damage,
        la_frost_weapon_damage=state.la_frost_weapon_damage,
        skill2_la_damage=state.skill2_la_damage,
        cp_la_damage=state.cp_la_damage,
        skill_la_damage=state.skill_la_damage,
        set_la_damage=state.set_la_damage,
        frost_damage_done=state.frost_damage_done,
        direct_damage_done=state.direct_damage_done,
        single_target_damage_done=state.single_target_damage_done,
        damage_done=state.damage_done,
    )


def calculate_shock_staff_light_attack(
    state: LightAttackState,
) -> float:
    return calculate_la_shock_staff(
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