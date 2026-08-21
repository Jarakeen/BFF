def calculate_frost_resist(
    *,
    item_frost_resist: float = 0.0,
    skill_frost_resist: float = 0.0,
) -> float:
    """
    UESP:

    FrostResist =
        Item.FrostResist + Skill.FrostResist
    """
    return item_frost_resist + skill_frost_resist


def calculate_flame_resist(
    *,
    item_flame_resist: float = 0.0,
    skill_flame_resist: float = 0.0,
) -> float:
    """
    UESP:

    FlameResist =
        Item.FlameResist + Skill.FlameResist
    """
    return item_flame_resist + skill_flame_resist


def calculate_shock_resist(
    *,
    item_shock_resist: float = 0.0,
    skill_shock_resist: float = 0.0,
) -> float:
    """
    UESP:

    ShockResist =
        Item.ShockResist + Skill.ShockResist
    """
    return item_shock_resist + skill_shock_resist


def calculate_poison_resist(
    *,
    item_poison_resist: float = 0.0,
    skill_poison_resist: float = 0.0,
) -> float:
    """
    UESP:

    PoisonResist =
        Item.PoisonResist + Skill.PoisonResist
    """
    return item_poison_resist + skill_poison_resist


def calculate_disease_resist(
    *,
    item_disease_resist: float = 0.0,
    skill_disease_resist: float = 0.0,
) -> float:
    """
    UESP:

    DiseaseResist =
        Item.DiseaseResist + Skill.DiseaseResist
    """
    return item_disease_resist + skill_disease_resist