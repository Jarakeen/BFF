from __future__ import annotations


def calculate_dot_damage_done(
    *,
    cp_dot_damage_done: float = 0.0,
    skill_dot_damage_done: float = 0.0,
    set_dot_damage_done: float = 0.0,
) -> float:
    return (
        cp_dot_damage_done
        + skill_dot_damage_done
        + set_dot_damage_done
    )


def calculate_direct_damage_done(
    *,
    cp_direct_damage_done: float = 0.0,
    skill_direct_damage_done: float = 0.0,
    set_direct_damage_done: float = 0.0,
) -> float:
    return (
        cp_direct_damage_done
        + skill_direct_damage_done
        + set_direct_damage_done
    )


def calculate_single_target_damage_done(
    *,
    skill_single_target_damage_done: float = 0.0,
    cp_single_target_damage_done: float = 0.0,
) -> float:
    return (
        skill_single_target_damage_done
        + cp_single_target_damage_done
    )


def calculate_aoe_damage_done(
    *,
    set_aoe_damage_done: float = 0.0,
    skill_aoe_damage_done: float = 0.0,
    cp_aoe_damage_done: float = 0.0,
) -> float:
    return (
        set_aoe_damage_done
        + skill_aoe_damage_done
        + cp_aoe_damage_done
    )


def calculate_magic_damage_done(
    *,
    cp_magic_damage_done: float = 0.0,
    skill_magic_damage_done: float = 0.0,
    buff_magic_damage_done: float = 0.0,
    item_magic_damage_done: float = 0.0,
    set_magic_damage_done: float = 0.0,
) -> float:
    return (
        cp_magic_damage_done
        + skill_magic_damage_done
        + buff_magic_damage_done
        + item_magic_damage_done
        + set_magic_damage_done
    )


def calculate_physical_damage_done(
    *,
    cp_physical_damage_done: float = 0.0,
    skill_physical_damage_done: float = 0.0,
    buff_physical_damage_done: float = 0.0,
    item_physical_damage_done: float = 0.0,
    set_physical_damage_done: float = 0.0,
) -> float:
    return (
        cp_physical_damage_done
        + skill_physical_damage_done
        + buff_physical_damage_done
        + item_physical_damage_done
        + set_physical_damage_done
    )


def calculate_shock_damage_done(
    *,
    cp_shock_damage_done: float = 0.0,
    skill_shock_damage_done: float = 0.0,
    buff_shock_damage_done: float = 0.0,
    item_shock_damage_done: float = 0.0,
    set_shock_damage_done: float = 0.0,
) -> float:
    return (
        cp_shock_damage_done
        + skill_shock_damage_done
        + buff_shock_damage_done
        + item_shock_damage_done
        + set_shock_damage_done
    )


def calculate_flame_damage_done(
    *,
    cp_flame_damage_done: float = 0.0,
    skill_flame_damage_done: float = 0.0,
    buff_flame_damage_done: float = 0.0,
    item_flame_damage_done: float = 0.0,
    set_flame_damage_done: float = 0.0,
) -> float:
    return (
        cp_flame_damage_done
        + skill_flame_damage_done
        + buff_flame_damage_done
        + item_flame_damage_done
        + set_flame_damage_done
    )


def calculate_frost_damage_done(
    *,
    cp_frost_damage_done: float = 0.0,
    skill_frost_damage_done: float = 0.0,
    buff_frost_damage_done: float = 0.0,
    item_frost_damage_done: float = 0.0,
    set_frost_damage_done: float = 0.0,
) -> float:
    return (
        cp_frost_damage_done
        + skill_frost_damage_done
        + buff_frost_damage_done
        + item_frost_damage_done
        + set_frost_damage_done
    )


def calculate_poison_damage_done(
    *,
    cp_poison_damage_done: float = 0.0,
    skill_poison_damage_done: float = 0.0,
    buff_poison_damage_done: float = 0.0,
    item_poison_damage_done: float = 0.0,
    set_poison_damage_done: float = 0.0,
) -> float:
    return (
        cp_poison_damage_done
        + skill_poison_damage_done
        + buff_poison_damage_done
        + item_poison_damage_done
        + set_poison_damage_done
    )


def calculate_disease_damage_done(
    *,
    cp_disease_damage_done: float = 0.0,
    skill_disease_damage_done: float = 0.0,
    buff_disease_damage_done: float = 0.0,
    item_disease_damage_done: float = 0.0,
    set_disease_damage_done: float = 0.0,
) -> float:
    return (
        cp_disease_damage_done
        + skill_disease_damage_done
        + buff_disease_damage_done
        + item_disease_damage_done
        + set_disease_damage_done
    )


def calculate_bow_damage_done(
    *,
    cp_bow_damage_done: float = 0.0,
    skill_bow_damage_done: float = 0.0,
    buff_bow_damage_done: float = 0.0,
    item_bow_damage_done: float = 0.0,
    set_bow_damage_done: float = 0.0,
) -> float:
    return (
        cp_bow_damage_done
        + skill_bow_damage_done
        + buff_bow_damage_done
        + item_bow_damage_done
        + set_bow_damage_done
    )


def calculate_bleed_damage_done(
    *,
    set_bleed_damage_done: float = 0.0,
    skill_bleed_damage_done: float = 0.0,
) -> float:
    return (
        set_bleed_damage_done
        + skill_bleed_damage_done
    )


def calculate_pet_damage_done(
    *,
    skill_pet_damage_done: float = 0.0,
    set_pet_damage_done: float = 0.0,
) -> float:
    return (
        skill_pet_damage_done
        + set_pet_damage_done
    )


def calculate_damage_done(
    *,
    cp_damage_done: float = 0.0,
    skill_damage_done: float = 0.0,
    buff_damage_done: float = 0.0,
    item_damage_done: float = 0.0,
    set_damage_done: float = 0.0,
) -> float:
    return (
        cp_damage_done
        + skill_damage_done
        + buff_damage_done
        + item_damage_done
        + set_damage_done
    )