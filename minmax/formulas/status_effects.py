def calculate_poisoned_duration() -> float:
    """
    UESP:

    PoisonedDuration =
        6.0
    """
    return 6.0


def calculate_status_duration(
    *,
    set_status_effect_duration: float = 0.0,
) -> float:
    """
    UESP:

    StatusDuration =
        4.0 + Set.StatusEffectDuration
    """
    return 4.0 + set_status_effect_duration


def calculate_magical_enchant_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_magical_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MagicalEnchantStatusChance =
        (0.20) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MagicalStatusEffectChance
        )
    """
    return 0.20 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_magical_status_effect_chance
    )


def calculate_magical_ability_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_magical_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MagicalAbilityStatusChance =
        (0.10) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MagicalStatusEffectChance
        )
    """
    return 0.10 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_magical_status_effect_chance
    )


def calculate_magical_aoe_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_magical_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MagicalAOEStatusChance =
        (0.05) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MagicalStatusEffectChance
        )
    """
    return 0.05 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_magical_status_effect_chance
    )


def calculate_magical_dot_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_magical_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MagicalDOTStatusChance =
        (0.03) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MagicalStatusEffectChance
        )
    """
    return 0.03 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_magical_status_effect_chance
    )


def calculate_magical_aoe_dot_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_magical_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MagicalAOEDOTStatusChance =
        (0.01) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MagicalStatusEffectChance
        )
    """
    return 0.01 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_magical_status_effect_chance
    )


def calculate_martial_enchant_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_martial_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MartialEnchantStatusChance =
        (0.20) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MartialStatusEffectChance
        )
    """
    return 0.20 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_martial_status_effect_chance
    )


def calculate_martial_ability_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_martial_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MartialAbilityStatusChance =
        (0.10) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MartialStatusEffectChance
        )
    """
    return 0.10 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_martial_status_effect_chance
    )


def calculate_martial_aoe_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_martial_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MartialAOEStatusChance =
        (0.05) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MartialStatusEffectChance
        )
    """
    return 0.05 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_martial_status_effect_chance
    )


def calculate_martial_dot_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_martial_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MartialDOTStatusChance =
        (0.03) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MartialStatusEffectChance
        )
    """
    return 0.03 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_martial_status_effect_chance
    )


def calculate_martial_aoe_dot_status_chance(
    *,
    skill_status_effect_chance: float = 0.0,
    set_status_effect_chance: float = 0.0,
    item_status_effect_chance: float = 0.0,
    cp_martial_status_effect_chance: float = 0.0,
) -> float:
    """
    UESP:

    MartialAOEDOTStatusChance =
        (0.01) * (
            1
            + Skill.StatusEffectChance
            + Set.StatusEffectChance
            + Item.StatusEffectChance
            + CP.MartialStatusEffectChance
        )
    """
    return 0.01 * (
        1
        + skill_status_effect_chance
        + set_status_effect_chance
        + item_status_effect_chance
        + cp_martial_status_effect_chance
    )