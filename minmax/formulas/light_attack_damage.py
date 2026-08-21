import math


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