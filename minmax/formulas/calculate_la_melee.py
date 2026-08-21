import math


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