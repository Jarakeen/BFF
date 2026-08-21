def calculate_healing_done(
    *,
    item_healing_done: float = 0.0,
    set_healing_done: float = 0.0,
    skill_healing_done: float = 0.0,
    cp_healing_done: float = 0.0,
    buff_healing_done: float = 0.0,
    mundus_healing_done: float = 0.0,
) -> float:
    """
    UESP:

    HealingDone =
        Item.HealingDone
        + Set.HealingDone
        + Skill.HealingDone
        + CP.HealingDone
        + Buff.HealingDone
        + Mundus.HealingDone
    """
    return (
        item_healing_done
        + set_healing_done
        + skill_healing_done
        + cp_healing_done
        + buff_healing_done
        + mundus_healing_done
    )


def calculate_aoe_healing_done(
    *,
    skill_aoe_healing_done: float = 0.0,
    set_aoe_healing_done: float = 0.0,
    cp_aoe_healing_done: float = 0.0,
) -> float:
    """
    UESP:

    AOEHealingDone =
        Skill.AOEHealingDone
        + Set.AOEHealingDone
        + CP.AOEHealingDone
    """
    return (
        skill_aoe_healing_done
        + set_aoe_healing_done
        + cp_aoe_healing_done
    )


def calculate_dot_healing_done(
    *,
    skill_dot_healing_done: float = 0.0,
    set_dot_healing_done: float = 0.0,
    cp_dot_healing_done: float = 0.0,
) -> float:
    """
    UESP:

    DotHealingDone =
        Skill.DotHealingDone
        + Set.DotHealingDone
        + CP.DotHealingDone
    """
    return (
        skill_dot_healing_done
        + set_dot_healing_done
        + cp_dot_healing_done
    )


def calculate_single_target_healing_done(
    *,
    skill_single_target_healing_done: float = 0.0,
    set_single_target_healing_done: float = 0.0,
    cp_single_target_healing_done: float = 0.0,
) -> float:
    """
    UESP:

    SingleTargetHealingDone =
        Skill.SingleTargetHealingDone
        + Set.SingleTargetHealingDone
        + CP.SingleTargetHealingDone
    """
    return (
        skill_single_target_healing_done
        + set_single_target_healing_done
        + cp_single_target_healing_done
    )


def calculate_healing_taken(
    *,
    item_healing_taken: float = 0.0,
    set_healing_taken: float = 0.0,
    skill_healing_taken: float = 0.0,
    cp_healing_taken: float = 0.0,
    buff_healing_taken: float = 0.0,
) -> float:
    """
    UESP:

    HealingTaken =
        Item.HealingTaken
        + Set.HealingTaken
        + Skill.HealingTaken
        + CP.HealingTaken
        + Buff.HealingTaken
    """
    return (
        item_healing_taken
        + set_healing_taken
        + skill_healing_taken
        + cp_healing_taken
        + buff_healing_taken
    )


def calculate_healing_received(
    *,
    item_healing_received: float = 0.0,
    set_healing_received: float = 0.0,
    skill_healing_received: float = 0.0,
    cp_healing_received: float = 0.0,
    buff_healing_received: float = 0.0,
    skill2_healing_received: float = 0.0,
) -> float:
    """
    UESP:

    HealingReceived =
        (
            1
            + Item.HealingReceived
            + Set.HealingReceived
            + Skill.HealingReceived
            + CP.HealingReceived
            + Buff.HealingReceived
        )
        * (1 + Skill2.HealingReceived)
        - 1
    """
    return (
        (
            1
            + item_healing_received
            + set_healing_received
            + skill_healing_received
            + cp_healing_received
            + buff_healing_received
        )
        * (1 + skill2_healing_received)
        - 1
    )


def calculate_healing_total(
    *,
    healing_done: float,
    healing_taken: float,
    healing_received: float,
) -> float:
    """
    UESP:

    HealingTotal =
        (1 + HealingDone)
        * (1 + HealingTaken)
        * (1 + HealingReceived)
    """
    return (
        (1 + healing_done)
        * (1 + healing_taken)
        * (1 + healing_received)
    )


def calculate_resurrect_time(
    *,
    set_resurrect_speed: float = 0.0,
    skill_resurrect_speed: float = 0.0,
    buff_resurrect_speed: float = 0.0,
    cp_resurrect_speed: float = 0.0,
    item_resurrect_speed: float = 0.0,
) -> float:
    """
    UESP:

    ResurrectTime =
        (7)
        * (1 - Set.ResurrectSpeed)
        * (1 - Skill.ResurrectSpeed)
        * (1 - Buff.ResurrectSpeed)
        * (1 - CP.ResurrectSpeed)
        * (1 - Item.ResurrectSpeed)
    """
    return (
        7
        * (1 - set_resurrect_speed)
        * (1 - skill_resurrect_speed)
        * (1 - buff_resurrect_speed)
        * (1 - cp_resurrect_speed)
        * (1 - item_resurrect_speed)
    )


def calculate_healing_reduction(
    *,
    cp_healing_reduction: float = 0.0,
) -> float:
    """
    UESP:

    HealingReduction =
        CP.HealingReduction
    """
    return cp_healing_reduction


def calculate_health_restore(
    *,
    item_health_restore: float = 0.0,
    skill_health_restore: float = 0.0,
    buff_health_restore: float = 0.0,
    set_health_restore: float = 0.0,
) -> float:
    """
    UESP:

    HealthRestore =
        Item.HealthRestore
        + Skill.HealthRestore
        + Buff.HealthRestore
        + Set.HealthRestore
    """
    return (
        item_health_restore
        + skill_health_restore
        + buff_health_restore
        + set_health_restore
    )