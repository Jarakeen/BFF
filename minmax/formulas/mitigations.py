"""Attack/defense mitigation formulas translated from UESP."""


def calculate_dot_damage_taken(*, cp_dot_damage_taken=0.0, set_dot_damage_taken=0.0, skill_dot_damage_taken=0.0):
    return cp_dot_damage_taken + set_dot_damage_taken + skill_dot_damage_taken


def calculate_direct_damage_taken(*, cp_direct_damage_taken=0.0, set_direct_damage_taken=0.0):
    # Preserve the UESP source exactly: Set.DirectDamageTaken appears twice.
    return 1 + cp_direct_damage_taken + set_direct_damage_taken + set_direct_damage_taken


def calculate_single_target_damage_taken(*, cp_single_target_damage_taken=0.0, skill_single_target_damage_taken=0.0, set_single_target_damage_taken=0.0):
    return cp_single_target_damage_taken + skill_single_target_damage_taken + set_single_target_damage_taken


def calculate_aoe_damage_taken(*, cp_aoe_damage_taken=0.0, skill_aoe_damage_taken=0.0, set_aoe_damage_taken=0.0):
    return cp_aoe_damage_taken + skill_aoe_damage_taken + set_aoe_damage_taken


def calculate_magic_damage_taken(*, cp_magic_damage_taken=0.0, skill_magic_damage_taken=0.0):
    return (1 + cp_magic_damage_taken) * (1 + skill_magic_damage_taken) - 1


def calculate_physical_damage_taken(*, cp_physical_damage_taken=0.0, skill_physical_damage_taken=0.0):
    return (1 + cp_physical_damage_taken) * (1 + skill_physical_damage_taken) - 1


def calculate_ha_damage_taken(*, cp_ha_damage_taken=0.0):
    return 1 + cp_ha_damage_taken


def calculate_la_damage_taken(*, cp_la_damage_taken=0.0):
    return 1 + cp_la_damage_taken


def calculate_fall_damage_taken(*, cp_fall_damage_taken=0.0, set_fall_damage_taken=0.0):
    return 1 + cp_fall_damage_taken + set_fall_damage_taken


def calculate_damage_taken(*, cp_damage_taken=0.0, skill_damage_taken=0.0, buff_damage_taken=0.0,
                           item_damage_taken=0.0, set_damage_taken=0.0, buff_vulnerability=0.0):
    return ((1 - 0.15) * (1 + cp_damage_taken) * (1 + skill_damage_taken)
            * (1 + buff_damage_taken) * (1 + item_damage_taken)
            * (1 + set_damage_taken) + buff_vulnerability - 1)


def calculate_attack_spell_mitigation(*, target_spell_resist, target_spell_debuff=0.0,
                                      skill2_spell_penetration=0.0, spell_penetration=0.0,
                                      target_effective_level, target_defense_bonus=0.0):
    return (((min(33000, target_spell_resist) + target_spell_debuff)
             * (1 - skill2_spell_penetration) - spell_penetration)
            * (-1 / (target_effective_level * 1000)) + 1) * (1 - target_defense_bonus) * (-1) + 1


def calculate_attack_physical_mitigation(*, target_physical_resist, target_physical_debuff=0.0,
                                         skill2_physical_penetration=0.0, physical_penetration=0.0,
                                         target_effective_level, target_defense_bonus=0.0):
    return (((min(33000, target_physical_resist) + target_physical_debuff)
             * (1 - skill2_physical_penetration) - physical_penetration)
            * (-1 / (target_effective_level * 1000)) + 1) * (1 - target_defense_bonus) * (-1) + 1


def calculate_attack_spell_crit_damage(*, spell_crit_damage, target_crit_resist):
    return spell_crit_damage - target_crit_resist * (0.035 / 250)


def calculate_attack_weapon_crit_damage(*, weapon_crit_damage, target_crit_resist):
    return weapon_crit_damage - target_crit_resist * (0.035 / 250)


def calculate_defense_spell_mitigation(*, spell_resist, target_penetration_factor=0.0,
                                       target_penetration_flat=0.0, target_attack_bonus=0.0,
                                       magic_damage_taken=0.0, damage_taken=0.0, effective_level):
    return (((min(33000, spell_resist) * (1 - target_penetration_factor) - target_penetration_flat)
             * (-1 / (effective_level * 1000)) + 1)
            * (1 + target_attack_bonus) * (1 + magic_damage_taken) * (1 + damage_taken) * (-1) + 1)


def calculate_defense_physical_mitigation(*, physical_resist, target_penetration_factor=0.0,
                                          target_penetration_flat=0.0, target_attack_bonus=0.0,
                                          physical_damage_taken=0.0, damage_taken=0.0, effective_level):
    return (((min(33000, physical_resist) * (1 - target_penetration_factor) - target_penetration_flat)
             * (-1 / (effective_level * 1000)) + 1)
            * (1 + target_attack_bonus) * (1 + physical_damage_taken) * (1 + damage_taken) * (-1) + 1)


def calculate_defense_spell_aoe_mitigation(*, aoe_damage_taken, defense_spell_mitigation):
    return (1 + aoe_damage_taken) * (1 - defense_spell_mitigation) * (-1) + 1


def calculate_defense_physical_aoe_mitigation(*, aoe_damage_taken, defense_physical_mitigation):
    return (1 + aoe_damage_taken) * (1 - defense_physical_mitigation) * (-1) + 1


def calculate_defense_spell_dd_mitigation(*, direct_damage_taken, defense_spell_mitigation):
    return (1 + direct_damage_taken) * (1 - defense_spell_mitigation) * (-1) + 1


def calculate_defense_physical_dd_mitigation(*, direct_damage_taken, defense_physical_mitigation):
    return (1 + direct_damage_taken) * (1 - defense_physical_mitigation) * (-1) + 1


def calculate_defense_crit_dmg(*, target_crit_damage, crit_resist):
    return target_crit_damage - crit_resist * (0.035 / 250)
