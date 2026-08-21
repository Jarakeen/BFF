"""Additional direct translations from the UESP equation inventory."""

import math


def calculate_crit_resist(*, effective_level: float, item_crit_resist: float = 0.0,
                          set_crit_resist: float = 0.0, skill_crit_resist: float = 0.0,
                          cp_crit_resist: float = 0.0, buff_crit_resist: float = 0.0,
                          skill2_crit_resist: float = 0.0) -> float:
    """UESP CritResist."""
    return (1320 + item_crit_resist + set_crit_resist + skill_crit_resist
            + cp_crit_resist + buff_crit_resist
            + round(skill2_crit_resist * effective_level * 100))


def calculate_magicka_restore(*, item_magicka_restore: float = 0.0,
                              skill_magicka_restore: float = 0.0,
                              buff_magicka_restore: float = 0.0,
                              set_magicka_restore: float = 0.0) -> float:
    """UESP MagickaRestore."""
    return item_magicka_restore + skill_magicka_restore + buff_magicka_restore + set_magicka_restore


def calculate_stamina_restore(*, item_stamina_restore: float = 0.0,
                              skill_stamina_restore: float = 0.0,
                              buff_stamina_restore: float = 0.0,
                              set_stamina_restore: float = 0.0) -> float:
    """UESP StaminaRestore."""
    return item_stamina_restore + skill_stamina_restore + buff_stamina_restore + set_stamina_restore


def calculate_mount_run_speed(*, base_walk_speed: float, mount_speed_bonus: float = 0.0,
                              skill_mount_speed: float = 0.0, cp_mount_speed: float = 0.0,
                              set_mount_speed: float = 0.0, buff_mount_speed: float = 0.0) -> float:
    """UESP MountRunSpeed."""
    return (base_walk_speed * (1 + 0.45 + mount_speed_bonus + skill_mount_speed + cp_mount_speed)
            * (1 + set_mount_speed + buff_mount_speed))


def calculate_overload_damage(*, cp_overload_damage: float = 0.0,
                              skill_overload_damage: float = 0.0,
                              set_overload_damage: float = 0.0,
                              buff_overload_damage: float = 0.0) -> float:
    """UESP OverloadDamage."""
    return cp_overload_damage + skill_overload_damage + set_overload_damage + buff_overload_damage


def calculate_haspeed() -> float:
    """UESP HASpeed = 1."""
    return 1.0


def calculate_la_bow(*, magicka: float, stamina: float,
                     la_physical_weapon_damage: float, la_physical_spell_damage: float,
                     skill2_la_damage: float = 0.0, cp_la_damage: float = 0.0,
                     skill_la_damage: float = 0.0, set_la_damage: float = 0.0,
                     bow_damage_done: float = 0.0, physical_damage_done: float = 0.0,
                     damage_done: float = 0.0, direct_damage_done: float = 0.0,
                     single_target_damage_done: float = 0.0,
                     skill_line_damage_bow: float = 0.0) -> float:
    """UESP LABow."""
    base = min(math.floor(0.045 * max(magicka, stamina))
               + math.floor(0.4725 * max(la_physical_weapon_damage, la_physical_spell_damage)), 3465)
    return (base + skill2_la_damage) * (1 + cp_la_damage + skill_la_damage + set_la_damage
        + bow_damage_done + physical_damage_done + damage_done + direct_damage_done
        + single_target_damage_done + skill_line_damage_bow)


def calculate_la_overload(*, magicka: float, stamina: float,
                          la_physical_weapon_damage: float, la_physical_spell_damage: float,
                          skill2_la_damage: float = 0.0, cp_la_damage: float = 0.0,
                          skill_la_damage: float = 0.0, set_la_damage: float = 0.0,
                          shock_damage_done: float = 0.0, single_target_damage_done: float = 0.0,
                          direct_damage_done: float = 0.0, damage_done: float = 0.0,
                          overload_damage: float = 0.0) -> float:
    """UESP LAOverload."""
    return (math.floor(0.100 * max(magicka, stamina))
            + math.floor(1.050 * max(la_physical_weapon_damage, la_physical_spell_damage))
            + skill2_la_damage) * (1 + cp_la_damage + skill_la_damage + set_la_damage
            + shock_damage_done + single_target_damage_done + direct_damage_done
            + damage_done + overload_damage)


def calculate_divines(*, item_divines: float = 0.0) -> float:
    return item_divines


def calculate_training(*, item_training: float = 0.0) -> float:
    return item_training


def calculate_ultimate_restore(*, item_ultimate_restore: float = 0.0,
                               set_ultimate_restore: float = 0.0) -> float:
    return item_ultimate_restore + set_ultimate_restore


def calculate_potion_duration(*, item_potion_duration: float = 0.0,
                              skill_potion_duration: float = 0.0) -> float:
    return item_potion_duration + skill_potion_duration


def calculate_potion_cooldown(*, item_potion_duration: float = 0.0,
                              skill_potion_duration: float = 0.0,
                              set_potion_duration: float = 0.0) -> float:
    return item_potion_duration + skill_potion_duration + set_potion_duration


def calculate_constitution(*, armor_heavy: float, set_constitution: float = 0.0) -> float:
    return 108 * armor_heavy * (1 + set_constitution)
