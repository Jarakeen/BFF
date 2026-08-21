"""Heavy-attack damage and resource formulas translated from UESP."""

import math


def _restore_sta(base, cp=0.0, skill=0.0, set_=0.0, buff=0.0):
    return base * (1 + cp) * (1 + skill + set_ + buff)


def calculate_ha_restore_bow(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0):
    return _restore_sta(2772, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore)


def calculate_ha_restore_dw(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0):
    return _restore_sta(2095, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore)


def calculate_ha_restore_2h(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0):
    return _restore_sta(2425, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore)


def calculate_ha_restore_1hs(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0):
    return _restore_sta(2293, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore)


def calculate_ha_restore_fire_frost_staff(*, skill2_ha_mag_restore=0.0, cp_ha_mag_restore=0.0, skill_ha_mag_restore=0.0, set_ha_mag_restore=0.0, buff_ha_mag_restore=0.0):
    return (2838 + skill2_ha_mag_restore) * (1 + cp_ha_mag_restore) * (1 + skill_ha_mag_restore + set_ha_mag_restore + buff_ha_mag_restore)


def calculate_ha_restore_shock_staff(*, skill2_ha_mag_restore=0.0, cp_ha_mag_restore=0.0, skill_ha_mag_restore=0.0, set_ha_mag_restore=0.0, buff_ha_mag_restore=0.0):
    return (2970 + skill2_ha_mag_restore) * (1 + cp_ha_mag_restore) * (1 + skill_ha_mag_restore + set_ha_mag_restore + buff_ha_mag_restore)


def calculate_ha_restore_rest_staff(*, skill2_ha_mag_restore=0.0, cp_ha_mag_restore=0.0, skill_ha_mag_restore=0.0, set_ha_mag_restore=0.0, buff_ha_mag_restore=0.0, skill_ha_mag_restore_rest_staff=0.0):
    return (2970 + skill2_ha_mag_restore) * (1 + cp_ha_mag_restore) * (1 + skill_ha_mag_restore + set_ha_mag_restore + buff_ha_mag_restore) * (1 + skill_ha_mag_restore_rest_staff)


def calculate_ha_restore_unarmed(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0):
    return _restore_sta(2095, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore)


def calculate_ha_restore_werewolf(*, cp_ha_sta_restore=0.0, skill_ha_sta_restore=0.0, set_ha_sta_restore=0.0, buff_ha_sta_restore=0.0, skill_ha_sta_restore_werewolf=0.0):
    return _restore_sta(3235, cp_ha_sta_restore, skill_ha_sta_restore, set_ha_sta_restore, buff_ha_sta_restore) * (1 + skill_ha_sta_restore_werewolf)


def calculate_ha_flame_spell_damage(*, spell_damage, skill_bonus_spell_damage_flame, skill2_ha_spell_damage=0.0, buff_spell_damage=0.0, skill_spell_damage=0.0):
    return spell_damage + (skill_bonus_spell_damage_flame + skill2_ha_spell_damage) * (1 + buff_spell_damage + skill_spell_damage)


def calculate_ha_flame_weapon_damage(*, weapon_damage, skill_bonus_weapon_damage_flame, skill2_ha_weapon_damage=0.0, buff_weapon_damage=0.0, skill_weapon_damage=0.0):
    return weapon_damage + (skill_bonus_weapon_damage_flame + skill2_ha_weapon_damage) * (1 + buff_weapon_damage + skill_weapon_damage)


def calculate_ha_shock_spell_damage(*, spell_damage, skill_bonus_spell_damage_shock, skill2_ha_spell_damage=0.0, item_channel_spell_damage=0.0, buff_spell_damage=0.0, skill_spell_damage=0.0):
    return spell_damage + (skill_bonus_spell_damage_shock + skill2_ha_spell_damage + item_channel_spell_damage) * (1 + buff_spell_damage + skill_spell_damage)


def calculate_ha_shock_weapon_damage(*, weapon_damage, skill_bonus_weapon_damage_shock, skill2_ha_weapon_damage=0.0, item_channel_weapon_damage=0.0, buff_weapon_damage=0.0, skill_weapon_damage=0.0):
    return weapon_damage + (skill_bonus_weapon_damage_shock + skill2_ha_weapon_damage + item_channel_weapon_damage) * (1 + buff_weapon_damage + skill_weapon_damage)


def calculate_ha_frost_spell_damage(*, spell_damage, skill_bonus_spell_damage_frost, skill2_la_spell_damage=0.0, buff_spell_damage=0.0, skill_spell_damage=0.0):
    return spell_damage + (skill_bonus_spell_damage_frost + skill2_la_spell_damage) * (1 + buff_spell_damage + skill_spell_damage)


def calculate_ha_frost_weapon_damage(*, weapon_damage, skill_bonus_weapon_damage_frost, skill2_la_weapon_damage=0.0, buff_weapon_damage=0.0, skill_weapon_damage=0.0):
    return weapon_damage + (skill_bonus_weapon_damage_frost + skill2_la_weapon_damage) * (1 + buff_weapon_damage + skill_weapon_damage)


def calculate_ha_magic_spell_damage(*, spell_damage, skill_bonus_spell_damage_magic, skill2_ha_spell_damage=0.0, item_channel_spell_damage=0.0, buff_spell_damage=0.0, skill_spell_damage=0.0):
    return spell_damage + (skill_bonus_spell_damage_magic + skill2_ha_spell_damage + item_channel_spell_damage) * (1 + buff_spell_damage + skill_spell_damage)


def calculate_ha_magic_weapon_damage(*, weapon_damage, skill_bonus_weapon_damage_magic, skill2_ha_weapon_damage=0.0, item_channel_weapon_damage=0.0, buff_weapon_damage=0.0, skill_weapon_damage=0.0):
    return weapon_damage + (skill_bonus_weapon_damage_magic + skill2_ha_weapon_damage + item_channel_weapon_damage) * (1 + buff_weapon_damage + skill_weapon_damage)


def calculate_ha_physical_weapon_damage(*, weapon_damage, skill_bonus_weapon_damage_physical, skill2_ha_weapon_damage=0.0):
    return weapon_damage + skill_bonus_weapon_damage_physical + skill2_ha_weapon_damage


def calculate_ha_physical_spell_damage(*, spell_damage, skill_bonus_spell_damage_physical, skill2_ha_spell_damage=0.0, buff_spell_damage=0.0, skill_spell_damage=0.0):
    return spell_damage + (skill_bonus_spell_damage_physical + skill2_ha_spell_damage) * (1 + buff_spell_damage + skill_spell_damage)


def _ha_base(magicka, stamina, spell_damage, weapon_damage, magicka_ratio, power_ratio, skill2, cp, skill, set_, typed, direct, single, damage, empower):
    return (math.floor(magicka_ratio * max(magicka, stamina))
            + math.floor(power_ratio * max(spell_damage, weapon_damage))
            + skill2) * (1 + cp + skill + set_ + typed + direct + single + damage + empower)


def calculate_ha_flame_staff(*, magicka, stamina, ha_flame_spell_damage, ha_flame_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, flame_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_flame_spell_damage, ha_flame_weapon_damage, 0.071429, 0.750, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, flame_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_frost_staff(*, magicka, stamina, ha_frost_spell_damage, ha_frost_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, frost_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_frost_spell_damage, ha_frost_weapon_damage, 0.071429, 0.750, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, frost_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_shock_staff_final(*, magicka, stamina, ha_shock_spell_damage, ha_shock_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, shock_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_shock_spell_damage, ha_shock_weapon_damage, 0.065714, 0.690, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, shock_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_shock_staff(*, magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, shock_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0, ha_shock_staff_final=0.0):
    first = _ha_base(magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, 0.021905, 0.23, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, shock_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower) * 2
    return first + ha_shock_staff_final


def calculate_ha_restoration_final(*, magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, magic_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, 0.071429, 0.75, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, magic_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_restoration(*, magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, magic_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0, ha_restoration_final=0.0):
    first = _ha_base(magicka, stamina, la_magic_spell_damage, la_magic_weapon_damage, 0.01369, 0.14375, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, magic_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower) * 2
    return first + ha_restoration_final


def calculate_ha_unarmed(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, physical_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, 0.0700, 0.7350, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, physical_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_one_hand(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, physical_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, 0.066667, 0.700, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, physical_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_two_hand(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, physical_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, 0.071429, 0.750, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, physical_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_dual_wield(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, physical_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0, skill_line_damage_dual_wield=0.0):
    one = math.floor(0.023810 * max(magicka, stamina)) + math.floor(0.250 * max(ha_physical_weapon_damage, ha_physical_spell_damage))
    return (one + one + skill2_ha_damage) * (1 + cp_ha_damage + skill_ha_damage + set_ha_damage + physical_damage_done + direct_damage_done + single_target_damage_done + damage_done + empower + skill_line_damage_dual_wield)


def calculate_ha_werewolf(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, physical_damage_done=0.0, direct_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0):
    return _ha_base(magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, 0.071429, 0.750, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, physical_damage_done, direct_damage_done, single_target_damage_done, damage_done, empower)


def calculate_ha_overload(*, magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, skill2_ha_damage=0.0, cp_ha_damage=0.0, skill_ha_damage=0.0, set_ha_damage=0.0, shock_damage_done=0.0, aoe_damage_done=0.0, single_target_damage_done=0.0, damage_done=0.0, empower=0.0, overload_damage=0.0):
    return _ha_base(magicka, stamina, ha_physical_weapon_damage, ha_physical_spell_damage, 0.0900, 0.945, skill2_ha_damage, cp_ha_damage, skill_ha_damage, set_ha_damage, shock_damage_done, aoe_damage_done, single_target_damage_done, damage_done, empower + overload_damage)


def calculate_ha_speed() -> float:
    return 1.0
