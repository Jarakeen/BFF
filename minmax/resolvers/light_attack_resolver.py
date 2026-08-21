from __future__ import annotations

from minmax.combat_state import LightAttackState


def resolve_light_attack_state(
    *,
    magicka: float,
    stamina: float,
    la_flame_spell_damage: float = 0.0,
    la_flame_weapon_damage: float = 0.0,
    la_frost_spell_damage: float = 0.0,
    la_frost_weapon_damage: float = 0.0,
    la_shock_spell_damage: float = 0.0,
    la_shock_weapon_damage: float = 0.0,
    skill2_la_damage: float = 0.0,
    cp_la_damage: float = 0.0,
    skill_la_damage: float = 0.0,
    set_la_damage: float = 0.0,
    skill_ha_damage: float = 0.0,
    set_ha_damage: float = 0.0,
    buff_empower: float = 0.0,
    flame_damage_done: float = 0.0,
    frost_damage_done: float = 0.0,
    shock_damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    dot_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> LightAttackState:
    """Construct a resolved LightAttackState.

    This function performs NO combat calculations.

    Its only responsibility is to take already-resolved values and place
    them into the state consumed by the light-attack calculators.

    Database/effect resolution belongs upstream.
    UESP arithmetic belongs downstream in the formula functions.
    """

    return LightAttackState(
        magicka=magicka,
        stamina=stamina,
        la_flame_spell_damage=la_flame_spell_damage,
        la_flame_weapon_damage=la_flame_weapon_damage,
        la_frost_spell_damage=la_frost_spell_damage,
        la_frost_weapon_damage=la_frost_weapon_damage,
        la_shock_spell_damage=la_shock_spell_damage,
        la_shock_weapon_damage=la_shock_weapon_damage,
        skill2_la_damage=skill2_la_damage,
        cp_la_damage=cp_la_damage,
        skill_la_damage=skill_la_damage,
        set_la_damage=set_la_damage,
        skill_ha_damage=skill_ha_damage,
        set_ha_damage=set_ha_damage,
        buff_empower=buff_empower,
        flame_damage_done=flame_damage_done,
        frost_damage_done=frost_damage_done,
        shock_damage_done=shock_damage_done,
        direct_damage_done=direct_damage_done,
        single_target_damage_done=single_target_damage_done,
        dot_damage_done=dot_damage_done,
        damage_done=damage_done,
    )