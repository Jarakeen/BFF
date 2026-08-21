def calculate_bloodthirsty_spell_damage(
    *,
    target_percent_health: float,
    item_bloodthirsty: float = 0.0,
) -> float:
    """
    UESP:

    BloodthirstySpellDamage =
        (1 - min(0.9, Target.PercentHealth) / 0.9)
        * Item.Bloodthirsty
    """
    return (
        1
        - min(0.9, target_percent_health) / 0.9
    ) * item_bloodthirsty


def calculate_bloodthirsty_weapon_damage(
    *,
    target_percent_health: float,
    item_bloodthirsty: float = 0.0,
) -> float:
    """
    UESP:

    BloodthirstyWeaponDamage =
        (1 - min(0.9, Target.PercentHealth) / 0.9)
        * Item.Bloodthirsty
    """
    return (
        1
        - min(0.9, target_percent_health) / 0.9
    ) * item_bloodthirsty


def calculate_ultimate_restore(
    *,
    item_ultimate_restore: float = 0.0,
    set_ultimate_restore: float = 0.0,
) -> float:
    """
    UESP:

    UltimateRestore =
        Item.UltimateRestore + Set.UltimateRestore
    """
    return item_ultimate_restore + set_ultimate_restore


def calculate_potion_duration(
    *,
    item_potion_duration: float = 0.0,
    skill_potion_duration: float = 0.0,
) -> float:
    """
    UESP:

    PotionDuration =
        Item.PotionDuration + Skill.PotionDuration
    """
    return item_potion_duration + skill_potion_duration


def calculate_potion_cooldown(
    *,
    item_potion_duration: float = 0.0,
    skill_potion_duration: float = 0.0,
    set_potion_duration: float = 0.0,
) -> float:
    """
    UESP:

    PotionCooldown =
        Item.PotionDuration
        + Skill.PotionDuration
        + Set.PotionDuration
    """
    return (
        item_potion_duration
        + skill_potion_duration
        + set_potion_duration
    )


def calculate_sneak_cost(
    *,
    cp_sneak_cost: float = 0.0,
    skill_sneak_cost: float = 0.0,
    item_sneak_cost: float = 0.0,
    set_sneak_cost: float = 0.0,
    buff_sneak_cost: float = 0.0,
) -> float:
    """
    UESP:

    SneakCost =
        (133)
        * (1 + CP.SneakCost)
        * (1 + Skill.SneakCost)
        * (1 + Item.SneakCost)
        * (1 + Set.SneakCost)
        * (1 + Buff.SneakCost)
    """
    return (
        133
        * (1 + cp_sneak_cost)
        * (1 + skill_sneak_cost)
        * (1 + item_sneak_cost)
        * (1 + set_sneak_cost)
        * (1 + buff_sneak_cost)
    )