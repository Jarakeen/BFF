def calculate_la_flame_spell_damage(
    *,
    spell_damage: float,
    skill_bonus_spell_damage_flame: float,
    skill2_la_spell_damage: float = 0.0,
    buff_spell_damage: float = 0.0,
    skill_spell_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAFlameSpellDamage =
        SpellDamage
        + (SkillBonusSpellDmg.Flame + Skill2.LASpellDamage)
        * (1 + Buff.SpellDamage + Skill.SpellDamage)
    """
    return (
        spell_damage
        + (
            skill_bonus_spell_damage_flame
            + skill2_la_spell_damage
        )
        * (1 + buff_spell_damage + skill_spell_damage)
    )


def calculate_la_flame_weapon_damage(
    *,
    weapon_damage: float,
    skill_bonus_weapon_damage_flame: float,
    skill2_la_weapon_damage: float = 0.0,
    buff_weapon_damage: float = 0.0,
    skill_weapon_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAFlameWeaponDamage =
        WeaponDamage
        + (SkillBonusWeaponDmg.Flame + Skill2.LAWeaponDamage)
        * (1 + Buff.WeaponDamage + Skill.WeaponDamage)
    """
    return (
        weapon_damage
        + (
            skill_bonus_weapon_damage_flame
            + skill2_la_weapon_damage
        )
        * (1 + buff_weapon_damage + skill_weapon_damage)
    )


def calculate_la_shock_spell_damage(
    *,
    spell_damage: float,
    skill_bonus_spell_damage_shock: float,
    skill2_la_spell_damage: float = 0.0,
    item_channel_spell_damage: float = 0.0,
    buff_spell_damage: float = 0.0,
    skill_spell_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAShockSpellDamage =
        SpellDamage
        + (
            SkillBonusSpellDmg.Shock
            + Skill2.LASpellDamage
            + Item.ChannelSpellDamage
        )
        * (1 + Buff.SpellDamage + Skill.SpellDamage)
    """
    return (
        spell_damage
        + (
            skill_bonus_spell_damage_shock
            + skill2_la_spell_damage
            + item_channel_spell_damage
        )
        * (1 + buff_spell_damage + skill_spell_damage)
    )

def calculate_la_shock_weapon_damage(
    *,
    weapon_damage: float,
    skill_bonus_weapon_damage_shock: float,
    skill2_la_weapon_damage: float = 0.0,
    item_channel_weapon_damage: float = 0.0,
    buff_weapon_damage: float = 0.0,
    skill_weapon_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAShockWeaponDamage =
        WeaponDamage
        + (SkillBonusWeaponDmg.Shock
        + Skill2.LAWeaponDamage
        + Item.ChannelWeaponDamage)
        * (1 + Buff.WeaponDamage + Skill.WeaponDamage)
    """
    return (
        weapon_damage
        + (
            skill_bonus_weapon_damage_shock
            + skill2_la_weapon_damage
            + item_channel_weapon_damage
        )
        * (1 + buff_weapon_damage + skill_weapon_damage)
    )


def calculate_la_frost_spell_damage(
    *,
    spell_damage: float,
    skill_bonus_spell_damage_frost: float,
    skill2_la_spell_damage: float = 0.0,
    buff_spell_damage: float = 0.0,
    skill_spell_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAFrostSpellDamage =
        SpellDamage
        + (SkillBonusSpellDmg.Frost + Skill2.LASpellDamage)
        * (1 + Buff.SpellDamage + Skill.SpellDamage)
    """
    return (
        spell_damage
        + (
            skill_bonus_spell_damage_frost
            + skill2_la_spell_damage
        )
        * (1 + buff_spell_damage + skill_spell_damage)
    )


def calculate_la_frost_weapon_damage(
    *,
    weapon_damage: float,
    skill_bonus_weapon_damage_frost: float,
    skill2_la_weapon_damage: float = 0.0,
    buff_weapon_damage: float = 0.0,
    skill_weapon_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAFrostWeaponDamage =
        WeaponDamage
        + (SkillBonusWeaponDmg.Frost + Skill2.LAWeaponDamage)
        * (1 + Buff.WeaponDamage + Skill.WeaponDamage)
    """
    return (
        weapon_damage
        + (
            skill_bonus_weapon_damage_frost
            + skill2_la_weapon_damage
        )
        * (1 + buff_weapon_damage + skill_weapon_damage)
    )


def calculate_la_magic_spell_damage(
    *,
    spell_damage: float,
    skill_bonus_spell_damage_magic: float,
    skill2_la_spell_damage: float = 0.0,
    item_channel_spell_damage: float = 0.0,
    buff_spell_damage: float = 0.0,
    skill_spell_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAMagicSpellDamage =
        SpellDamage
        + (SkillBonusSpellDmg.Magic + Skill2.LASpellDamage
        + Item.ChannelSpellDamage)
        * (1 + Buff.SpellDamage + Skill.SpellDamage)

    The source contains this exact equation three times.
    It is represented once here.
    """
    return (
        spell_damage
        + (
            skill_bonus_spell_damage_magic
            + skill2_la_spell_damage
            + item_channel_spell_damage
        )
        * (1 + buff_spell_damage + skill_spell_damage)
    )


def calculate_la_physical_weapon_damage(
    *,
    weapon_damage: float,
    skill_bonus_weapon_damage_physical: float,
    skill2_la_weapon_damage: float = 0.0,
    buff_weapon_damage: float = 0.0,
    skill_weapon_damage: float = 0.0,
) -> float:
    """
    UESP:

    LAPhysicalWeaponDamage =
        WeaponDamage
        + (SkillBonusWeaponDmg.Physical + Skill2.LAWeaponDamage)
        * (1 + Buff.WeaponDamage + Skill.WeaponDamage)
    """
    return (
        weapon_damage
        + (
            skill_bonus_weapon_damage_physical
            + skill2_la_weapon_damage
        )
        * (1 + buff_weapon_damage + skill_weapon_damage)
    )