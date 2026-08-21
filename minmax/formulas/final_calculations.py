import math
import pytest

def calculate_la_speed(
    *,
    set_la_speed: float = 0.0,
) -> float:
    """
    Calculate light attack speed multiplier.

    UESP:

    LASpeed =
        1 + Set.LASpeed
    """
    return 1 + set_la_speed


def calculate_la_melee_speed(
    *,
    set_la_speed: float = 0.0,
    set_la_melee_speed: float = 0.0,
) -> float:
    """
    Calculate melee light attack speed multiplier.

    UESP:

    LAMeleeSpeed =
        1 + Set.LASpeed + Set.LAMeleeSpeed
    """
    return (
        1
        + set_la_speed
        + set_la_melee_speed
    )



def calculate_la_melee(
    *,
    magicka: float,
    stamina: float,
    la_physical_weapon_damage: float,
    la_physical_spell_damage: float,
    skill2_la_damage: float = 0.0,
    cp_la_damage: float = 0.0,
    skill_la_damage: float = 0.0,
    set_la_damage: float = 0.0,
    set_la_melee_damage: float = 0.0,
    physical_damage_done: float = 0.0,
    damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
) -> float:
    """
    Calculate the shared light-attack formula used by:

        LAUnarmed
        LAOneHand
        LATwoHand
        LAWerewolf

    UESP source:

    (min(
        floor(fround(0.05) * max(Magicka, Stamina))
        + floor(
            fround(0.550)
            * max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)
        ),
        3850
    ) + Skill2.LADamage)
    * (
        1
        + CP.LADamage
        + Skill.LADamage
        + Set.LADamage
        + Set.LAMeleeDamage
        + PhysicalDamageDone
        + DamageDone
        + DirectDamageDone
        + SingleTargetDamageDone
    )

    The four source equations are identical, so they are represented
    by one calculation rather than duplicating the same implementation.
    """

    base_damage = min(
        math.floor(
            0.05 * max(magicka, stamina)
        )
        + math.floor(
            0.550
            * max(
                la_physical_weapon_damage,
                la_physical_spell_damage,
            )
        ),
        3850,
    )

    return (
        base_damage + skill2_la_damage
    ) * (
        1
        + cp_la_damage
        + skill_la_damage
        + set_la_damage
        + set_la_melee_damage
        + physical_damage_done
        + damage_done
        + direct_damage_done
        + single_target_damage_done
    )

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

from math import floor

from .math_utils import fround


def calculate_status_spell_damage(
    *,
    spell_damage: float,
    skill_bonus_spell_damage: float,
    buff_spell_damage: float = 0.0,
    skill_spell_damage: float = 0.0,
) -> float:
    """
    UESP:

    StatusFlameSpellDamage =
        SpellDamage
        + (SkillBonusSpellDmg.X)
        * (1 + Buff.SpellDamage + Skill.SpellDamage)

    X represents the applicable damage type.
    """
    return (
        spell_damage
        + skill_bonus_spell_damage
        * (1 + buff_spell_damage + skill_spell_damage)
    )


def calculate_burning_damage(
    *,
    magicka: float,
    stamina: float,
    status_flame_spell_damage: float,
    status_flame_weapon_damage: float,
    burning_damage: float = 0.0,
    flame_damage_done: float = 0.0,
    dot_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    BurningDamage =
    (
        floor(fround(0.016) * max(Magicka, Stamina))
        + floor(
            fround(0.168)
            * max(StatusFlameSpellDamage, StatusFlameWeaponDamage)
        )
    )
    * (
        1
        + Skill.BurningDamage
        + FlameDamageDone
        + DotDamageDone
        + SingleTargetDamageDone
        + DamageDone
    )
    """
    base_damage = (
        floor(fround(0.016) * max(magicka, stamina))
        + floor(
            fround(0.168)
            * max(status_flame_spell_damage, status_flame_weapon_damage)
        )
    )

    multiplier = (
        1
        + burning_damage
        + flame_damage_done
        + dot_damage_done
        + single_target_damage_done
        + damage_done
    )

    return base_damage * multiplier


def calculate_chilled_damage(
    *,
    magicka: float,
    stamina: float,
    status_frost_spell_damage: float,
    status_frost_weapon_damage: float,
    frost_damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    ChilledDamage =
    (
        floor(fround(0.008) * max(Magicka, Stamina))
        + floor(
            fround(0.084)
            * max(StatusFrostSpellDamage, StatusFrostWeaponDamage)
        )
    )
    * (
        1
        + FrostDamageDone
        + DirectDamageDone
        + SingleTargetDamageDone
        + DamageDone
    )
    """
    base_damage = (
        floor(fround(0.008) * max(magicka, stamina))
        + floor(
            fround(0.084)
            * max(status_frost_spell_damage, status_frost_weapon_damage)
        )
    )

    multiplier = (
        1
        + frost_damage_done
        + direct_damage_done
        + single_target_damage_done
        + damage_done
    )

    return base_damage * multiplier


def calculate_concussion_damage(
    *,
    magicka: float,
    stamina: float,
    status_shock_spell_damage: float,
    status_shock_weapon_damage: float,
    shock_damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    ConcussionDamage =
    (
        floor(fround(0.008) * max(Magicka, Stamina))
        + floor(
            fround(0.084)
            * max(StatusShockSpellDamage, StatusShockWeaponDamage)
        )
    )
    * (
        1
        + ShockDamageDone
        + DirectDamageDone
        + SingleTargetDamageDone
        + DamageDone
    )
    """
    base_damage = (
        floor(fround(0.008) * max(magicka, stamina))
        + floor(
            fround(0.084)
            * max(status_shock_spell_damage, status_shock_weapon_damage)
        )
    )

    multiplier = (
        1
        + shock_damage_done
        + direct_damage_done
        + single_target_damage_done
        + damage_done
    )

    return base_damage * multiplier

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
