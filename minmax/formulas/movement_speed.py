def calculate_sprint_speed(
    *,
    base_walk_speed: float,
    set_sprint_speed: float = 0.0,
    buff_movement_speed: float = 0.0,
    item_movement_speed: float = 0.0,
    set_movement_speed: float = 0.0,
    buff_sprint_speed: float = 0.0,
    skill_movement_speed: float = 0.0,
    skill_sprint_speed: float = 0.0,
    cp_sprint_speed: float = 0.0,
    mundus_movement_speed: float = 0.0,
    cp_movement_speed: float = 0.0,
) -> float:
    """
    UESP:

    SprintSpeed =
        (BaseWalkSpeed)
        * min(
            2,
            1 + 0.40
            + Set.SprintSpeed
            + Buff.MovementSpeed
            + Item.MovementSpeed
            + Set.MovementSpeed
            + Buff.SprintSpeed
            + Skill.MovementSpeed
            + Skill.SprintSpeed
            + CP.SprintSpeed
            + Mundus.MovementSpeed
        )
        * (1 + CP.MovementSpeed)
    """
    return (
        base_walk_speed
        * min(
            2,
            1
            + 0.40
            + set_sprint_speed
            + buff_movement_speed
            + item_movement_speed
            + set_movement_speed
            + buff_sprint_speed
            + skill_movement_speed
            + skill_sprint_speed
            + cp_sprint_speed
            + mundus_movement_speed,
        )
        * (1 + cp_movement_speed)
    )


def calculate_swim_speed(
    *,
    base_walk_speed: float,
    skill_swim_speed: float = 0.0,
    buff_movement_speed: float = 0.0,
    mundus_movement_speed: float = 0.0,
    item_movement_speed: float = 0.0,
    set_movement_speed: float = 0.0,
    cp_movement_speed: float = 0.0,
) -> float:
    """
    UESP:

    SwimSpeed =
        (
            (BaseWalkSpeed) * (1 - 0.40)
            * (1 + Skill.SwimSpeed)
        )
        * (
            1
            + Buff.MovementSpeed
            + Mundus.MovementSpeed
            + Item.MovementSpeed
            + Set.MovementSpeed
            + CP.MovementSpeed
        )
    """
    return (
        (
            base_walk_speed
            * (1 - 0.40)
            * (1 + skill_swim_speed)
        )
        * (
            1
            + buff_movement_speed
            + mundus_movement_speed
            + item_movement_speed
            + set_movement_speed
            + cp_movement_speed
        )
    )


def calculate_sneak_speed(
    *,
    base_walk_speed: float,
    skill_normal_sneak_speed: float = 0.0,
    cp_sneak_speed: float = 0.0,
    skill_sneak_speed: float = 0.0,
    buff_movement_speed: float = 0.0,
    skill_movement_speed: float = 0.0,
    mundus_movement_speed: float = 0.0,
    item_movement_speed: float = 0.0,
    set_movement_speed: float = 0.0,
    skill2_sneak_speed: float = 0.0,
    cp_movement_speed: float = 0.0,
) -> float:
    """
    UESP:

    SneakSpeed =
        (
            (BaseWalkSpeed)
            * (
                1
                + (-0.40)
                * max(
                    0,
                    (
                        1
                        - Skill.NormalSneakSpeed
                        - CP.SneakSpeed
                    )
                    * (
                        1
                        - Skill.SneakSpeed
                    )
                )
                + Buff.MovementSpeed
                + Skill.MovementSpeed
                + Mundus.MovementSpeed
                + Item.MovementSpeed
                + Set.MovementSpeed
            )
        )
        * (
            1
            + Skill2.SneakSpeed
            + CP.MovementSpeed
        )
    """
    return (
        (
            base_walk_speed
            * (
                1
                + (-0.40)
                * max(
                    0,
                    (
                        1
                        - skill_normal_sneak_speed
                        - cp_sneak_speed
                    )
                    * (
                        1
                        - skill_sneak_speed
                    ),
                )
                + buff_movement_speed
                + skill_movement_speed
                + mundus_movement_speed
                + item_movement_speed
                + set_movement_speed
            )
        )
        * (
            1
            + skill2_sneak_speed
            + cp_movement_speed
        )
    )


def calculate_block_speed(
    *,
    base_walk_speed: float,
    skill_block_speed_penalty: float = 0.0,
    skill_block_speed: float = 0.0,
    cp_block_speed: float = 0.0,
) -> float:
    """
    UESP:

    BlockSpeed =
        (BaseWalkSpeed)
        * (1 - Skill.BlockSpeedPenalty)
        * (1 + Skill.BlockSpeed)
        * (1 + CP.BlockSpeed)
    """
    return (
        base_walk_speed
        * (1 - skill_block_speed_penalty)
        * (1 + skill_block_speed)
        * (1 + cp_block_speed)
    )


def calculate_mount_walk_speed(
    *,
    base_walk_speed: float,
    mount_speed_bonus: float = 0.0,
    skill_mount_speed: float = 0.0,
    cp_mount_speed: float = 0.0,
    set_mount_speed: float = 0.0,
    buff_mount_speed: float = 0.0,
) -> float:
    """
    UESP:

    MountWalkSpeed =
        (
            (BaseWalkSpeed)
            * (
                1
                + 0.15
                + MountSpeedBonus
                + Skill.MountSpeed
                + CP.MountSpeed
            )
        )
        * (
            1
            + Set.MountSpeed
            + Buff.MountSpeed
        )
    """
    return (
        (
            base_walk_speed
            * (
                1
                + 0.15
                + mount_speed_bonus
                + skill_mount_speed
                + cp_mount_speed
            )
        )
        * (
            1
            + set_mount_speed
            + buff_mount_speed
        )
    )