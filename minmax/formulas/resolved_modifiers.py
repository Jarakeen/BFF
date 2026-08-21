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


def calculate_la_flame_staff(
    *,
    magicka: float,
    stamina: float,
    la_flame_spell_damage: float,
    la_flame_weapon_damage: float,
    skill2_la_damage: float = 0.0,
    cp_la_damage: float = 0.0,
    skill_la_damage: float = 0.0,
    set_la_damage: float = 0.0,
    flame_damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    LAFlameStaff =
        (min(
            floor(fround(0.045) * max(Magicka, Stamina))
            + floor(fround(0.4725) * max(
                LAFlameSpellDamage,
                LAFlameWeaponDamage
            )),
            3465
        ) + Skill2.LADamage)
        * (
            1
            + CP.LADamage
            + Skill.LADamage
            + Set.LADamage
            + FlameDamageDone
            + DirectDamageDone
            + SingleTargetDamageDone
            + DamageDone
        )
    """
    base = min(
        math.floor(0.045 * max(magicka, stamina))
        + math.floor(
            0.4725 * max(
                la_flame_spell_damage,
                la_flame_weapon_damage,
            )
        ),
        3465,
    )

    return (
        base
        + skill2_la_damage
    ) * (
        1
        + cp_la_damage
        + skill_la_damage
        + set_la_damage
        + flame_damage_done
        + direct_damage_done
        + single_target_damage_done
        + damage_done
    )


def calculate_la_frost_staff(
    *,
    magicka: float,
    stamina: float,
    la_frost_spell_damage: float,
    la_frost_weapon_damage: float,
    skill2_la_damage: float = 0.0,
    cp_la_damage: float = 0.0,
    skill_la_damage: float = 0.0,
    set_la_damage: float = 0.0,
    frost_damage_done: float = 0.0,
    direct_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    LAFrostStaff =
        (min(
            floor(fround(0.045) * max(Magicka, Stamina))
            + floor(fround(0.4725) * max(
                LAFrostSpellDamage,
                LAFrostWeaponDamage
            )),
            3465
        ) + Skill2.LADamage)
        * (
            1
            + CP.LADamage
            + Skill.LADamage
            + Set.LADamage
            + FrostDamageDone
            + DirectDamageDone
            + SingleTargetDamageDone
            + DamageDone
        )
    """
    base = min(
        math.floor(0.045 * max(magicka, stamina))
        + math.floor(
            0.4725 * max(
                la_frost_spell_damage,
                la_frost_weapon_damage,
            )
        ),
        3465,
    )

    return (
        base
        + skill2_la_damage
    ) * (
        1
        + cp_la_damage
        + skill_la_damage
        + set_la_damage
        + frost_damage_done
        + direct_damage_done
        + single_target_damage_done
        + damage_done
    )


def calculate_la_shock_staff(
    *,
    magicka: float,
    stamina: float,
    la_shock_spell_damage: float,
    la_shock_weapon_damage: float,
    skill2_la_damage: float = 0.0,
    cp_la_damage: float = 0.0,
    skill_ha_damage: float = 0.0,
    set_ha_damage: float = 0.0,
    buff_empower: float = 0.0,
    shock_damage_done: float = 0.0,
    single_target_damage_done: float = 0.0,
    dot_damage_done: float = 0.0,
    damage_done: float = 0.0,
) -> float:
    """
    UESP:

    LAShockStaff =
        (min(
            floor(fround(0.045) * max(Magicka, Stamina))
            + floor(fround(0.4725) * max(
                LAShockSpellDamage,
                LAShockWeaponDamage
            )),
            3465
        ) + Skill2.LADamage)
        * (
            1
            + CP.LADamage
            + Skill.HADamage
            + Set.HADamage
            + Buff.Empower
            + ShockDamageDone
            + SingleTargetDamageDone
            + DotDamageDone
            + DamageDone
        )

    The Skill.HADamage / Set.HADamage / Buff.Empower /
    DotDamageDone terms are preserved exactly as written in
    equations.py.
    """
    base = min(
        math.floor(0.045 * max(magicka, stamina))
        + math.floor(
            0.4725 * max(
                la_shock_spell_damage,
                la_shock_weapon_damage,
            )
        ),
        3465,
    )

    return (
        base
        + skill2_la_damage
    ) * (
        1
        + cp_la_damage
        + skill_ha_damage
        + set_ha_damage
        + buff_empower
        + shock_damage_done
        + single_target_damage_done
        + dot_damage_done
        + damage_done
    )

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

def calculate_divines(
    *,
    item_divines: float = 0.0,
) -> float:
    """
    UESP:

    Divines =
        Item.Divines
    """
    return item_divines


def calculate_sturdy(
    *,
    item_sturdy: float = 0.0,
) -> float:
    """
    UESP:

    Sturdy =
        Item.Sturdy
    """
    return item_sturdy


def calculate_training(
    *,
    item_training: float = 0.0,
) -> float:
    """
    UESP:

    Training =
        Item.Training
    """
    return item_training


def calculate_bloodthirsty(
    *,
    item_bloodthirsty: float = 0.0,
) -> float:
    """
    UESP:

    Bloodthirsty =
        Item.Bloodthirsty
    """
    return item_bloodthirsty

import math
