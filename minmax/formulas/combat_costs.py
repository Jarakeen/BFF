def calculate_bash_cost(
    *,
    item_bash_cost: float = 0.0,
    cp_bash_cost: float = 0.0,
    skill_bash_cost: float = 0.0,
    set_bash_cost: float = 0.0,
) -> float:
    """
    UESP:

    BashCost =
        (765 + Item.BashCost)
        * (1 + CP.BashCost)
        * (1 + Skill.BashCost)
        * (1 + Set.BashCost)
    """
    return (
        (765 + item_bash_cost)
        * (1 + cp_bash_cost)
        * (1 + skill_bash_cost)
        * (1 + set_bash_cost)
    )


def calculate_bash_damage(
    *,
    spell_resist: float,
    physical_resist: float,
    cp_bash_damage: float = 0.0,
    skill2_bash_damage: float = 0.0,
    physical_damage_done: float = 0.0,
    damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    skill_bash_damage: float = 0.0,
    set_extra_bash_damage: float = 0.0,
    skill_extra_bash_damage: float = 0.0,
    item_extra_bash_damage: float = 0.0,
) -> float:
    """
    UESP:

    BashDamage =
        (
            max(SpellResist, PhysicalResist) * 0.011250
            + 1
            + CP.BashDamage
            + Skill2.BashDamage
        )
        * (
            1
            + PhysicalDamageDone
            + DamageDone
            + DirectDamageDone
            + SingleTargetDamageDone
            + Skill.BashDamage
        )
        + Set.ExtraBashDamage
        + Skill.ExtraBashDamage
        + Item.ExtraBashDamage
    """
    return (
        (
            max(spell_resist, physical_resist) * 0.011250
            + 1
            + cp_bash_damage
            + skill2_bash_damage
        )
        * (
            1
            + physical_damage_done
            + damage_done
            + direct_damage_done
            + single_target_damage_done
            + skill_bash_damage
        )
        + set_extra_bash_damage
        + skill_extra_bash_damage
        + item_extra_bash_damage
    )


def calculate_block_cost(
    *,
    item_block_cost: float = 0.0,
    item_sturdy: float = 0.0,
    cp_block_cost: float = 0.0,
    set_block_cost: float = 0.0,
    skill_block_cost: float = 0.0,
    buff_block_cost: float = 0.0,
    skill2_block_cost: float = 0.0,
) -> float:
    """
    UESP:

    BlockCost =
        (1750 + Item.BlockCost)
        * (1 - Item.Sturdy)
        * (1 + CP.BlockCost)
        * (1 + Set.BlockCost)
        * (1 + Skill.BlockCost)
        * (1 + Buff.BlockCost)
        * (1 + Skill2.BlockCost)
    """
    return (
        (1750 + item_block_cost)
        * (1 - item_sturdy)
        * (1 + cp_block_cost)
        * (1 + set_block_cost)
        * (1 + skill_block_cost)
        * (1 + buff_block_cost)
        * (1 + skill2_block_cost)
    )


def calculate_roll_dodge_cost(
    *,
    skill2_roll_dodge_cost: float = 0.0,
    cp_roll_dodge_cost: float = 0.0,
    skill_roll_dodge_cost: float = 0.0,
    item_roll_dodge_cost: float = 0.0,
    set_roll_dodge_cost: float = 0.0,
    buff_roll_dodge_cost: float = 0.0,
) -> float:
    """
    UESP:

    RollDodgeCost =
        (
            (4040 + Skill2.RollDodgeCost)
            * (1 + CP.RollDodgeCost)
        )
        * (
            Skill.RollDodgeCost
            + Item.RollDodgeCost
            + Set.RollDodgeCost
            + Buff.RollDodgeCost
            + 1
        )
    """
    return (
        (
            (4040 + skill2_roll_dodge_cost)
            * (1 + cp_roll_dodge_cost)
        )
        * (
            skill_roll_dodge_cost
            + item_roll_dodge_cost
            + set_roll_dodge_cost
            + buff_roll_dodge_cost
            + 1
        )
    )


def calculate_break_free_cost(
    *,
    skill2_break_free_cost: float = 0.0,
    cp_break_free_cost: float = 0.0,
    skill_break_free_cost: float = 0.0,
    buff_break_free_cost: float = 0.0,
    item_break_free_cost: float = 0.0,
    set_break_free_cost: float = 0.0,
) -> float:
    """
    UESP:

    BreakFreeCost =
        (
            (5400 + Skill2.BreakFreeCost)
            * (1 + CP.BreakFreeCost)
        )
        * (
            1
            + Skill.BreakFreeCost
            + Buff.BreakFreeCost
            + Item.BreakFreeCost
            + Set.BreakFreeCost
        )
    """
    return (
        (
            (5400 + skill2_break_free_cost)
            * (1 + cp_break_free_cost)
        )
        * (
            1
            + skill_break_free_cost
            + buff_break_free_cost
            + item_break_free_cost
            + set_break_free_cost
        )
    )


def calculate_fear_duration(
    *,
    cp_fear_duration: float = 0.0,
    set_crowd_control_duration: float = 0.0,
) -> float:
    """
    UESP:

    FearDuration =
        (4)
        * (1 + CP.FearDuration)
        * (1 + Set.CrowdControlDuration)
    """
    return (
        4
        * (1 + cp_fear_duration)
        * (1 + set_crowd_control_duration)
    )


def calculate_damage_shield(
    *,
    cp_damage_shield: float = 0.0,
    buff_damage_shield: float = 0.0,
    set_damage_shield: float = 0.0,
    skill_damage_shield: float = 0.0,
) -> float:
    """
    UESP:

    DamageShield =
        (1 + CP.DamageShield)
        * (1 + Buff.DamageShield)
        * (1 + Set.DamageShield)
        * (1 + Skill.DamageShield)
        + -1
    """
    return (
        (1 + cp_damage_shield)
        * (1 + buff_damage_shield)
        * (1 + set_damage_shield)
        * (1 + skill_damage_shield)
        - 1
    )


def calculate_damage_shield_cost(
    *,
    cp_damage_shield_cost: float = 0.0,
    skill_damage_shield_cost: float = 0.0,
) -> float:
    """
    UESP:

    DamageShieldCost =
        CP.DamageShieldCost + Skill.DamageShieldCost
    """
    return cp_damage_shield_cost + skill_damage_shield_cost