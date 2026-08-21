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