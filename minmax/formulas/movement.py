def calculate_sneak_range(
    *,
    skill2_sneak_range: float = 0.0,
    cp_sneak_range: float = 0.0,
    skill_sneak_range: float = 0.0,
    set_sneak_range: float = 0.0,
) -> float:
    """
    UESP:

    SneakRange =
        (max(0, 6.5 + Skill2.SneakRange + CP.SneakRange))
        * (Skill.SneakRange + Set.SneakRange + 1)
    """
    return (
        max(
            0,
            6.5
            + skill2_sneak_range
            + cp_sneak_range,
        )
        * (
            skill_sneak_range
            + set_sneak_range
            + 1
        )
    )


def calculate_sneak_detect_range(
    *,
    skill2_sneak_detect_range: float = 0.0,
    cp_sneak_detect_range: float = 0.0,
    item_sneak_detect_range: float = 0.0,
    skill_sneak_detect_range: float = 0.0,
    set_sneak_detect_range: float = 0.0,
) -> float:
    """
    UESP:

    SneakDetectRange =
        (max(0, 6.5 + Skill2.SneakDetectRange + CP.SneakDetectRange))
        * (1 + Item.SneakDetectRange
             + Skill.SneakDetectRange
             + Set.SneakDetectRange)
    """
    return (
        max(
            0,
            6.5
            + skill2_sneak_detect_range
            + cp_sneak_detect_range,
        )
        * (
            1
            + item_sneak_detect_range
            + skill_sneak_detect_range
            + set_sneak_detect_range
        )
    )


def calculate_sprint_cost(
    *,
    skill2_sprint_cost: float = 0.0,
    cp_sprint_cost: float = 0.0,
    buff_sprint_cost: float = 0.0,
    set_sprint_cost: float = 0.0,
    skill_sprint_cost: float = 0.0,
    item_sprint_cost: float = 0.0,
) -> float:
    """
    UESP:

    SprintCost =
        (500 + Skill2.SprintCost)
        * (1 + CP.SprintCost)
        * (1 + Buff.SprintCost)
        * (1 + Set.SprintCost)
        * (1 + Skill.SprintCost)
        * (1 + Item.SprintCost)
    """
    return (
        (500 + skill2_sprint_cost)
        * (1 + cp_sprint_cost)
        * (1 + buff_sprint_cost)
        * (1 + set_sprint_cost)
        * (1 + skill_sprint_cost)
        * (1 + item_sprint_cost)
    )


def calculate_walk_speed(
    *,
    base_walk_speed: float,
    buff_movement_speed: float = 0.0,
    skill_movement_speed: float = 0.0,
    item_movement_speed: float = 0.0,
    set_movement_speed: float = 0.0,
    mundus_movement_speed: float = 0.0,
    cp_movement_speed: float = 0.0,
) -> float:
    """
    UESP:

    WalkSpeed =
        ((BaseWalkSpeed) * (0.3))
        * (1 + Buff.MovementSpeed
             + Skill.MovementSpeed
             + Item.MovementSpeed
             + Set.MovementSpeed
             + Mundus.MovementSpeed)
        * (1 + CP.MovementSpeed)
    """
    return (
        (base_walk_speed * 0.3)
        * (
            1
            + buff_movement_speed
            + skill_movement_speed
            + item_movement_speed
            + set_movement_speed
            + mundus_movement_speed
        )
        * (1 + cp_movement_speed)
    )


def calculate_run_speed(
    *,
    base_walk_speed: float,
    buff_movement_speed: float = 0.0,
    skill_movement_speed: float = 0.0,
    item_movement_speed: float = 0.0,
    set_movement_speed: float = 0.0,
    mundus_movement_speed: float = 0.0,
    cp_movement_speed: float = 0.0,
) -> float:
    """
    UESP:

    RunSpeed =
        (BaseWalkSpeed)
        * (1 + Buff.MovementSpeed
             + Skill.MovementSpeed
             + Item.MovementSpeed
             + Set.MovementSpeed
             + Mundus.MovementSpeed)
        * (1 + CP.MovementSpeed)
    """
    return (
        base_walk_speed
        * (
            1
            + buff_movement_speed
            + skill_movement_speed
            + item_movement_speed
            + set_movement_speed
            + mundus_movement_speed
        )
        * (1 + cp_movement_speed)
    )