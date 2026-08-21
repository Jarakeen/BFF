"""Typed Python translations of UESP core-stat formulas.

Source of truth: ``services/minmax/equations.py`` (do not edit that file).

This module converts ONLY the following formulas, exactly as documented:
    - Max Health / Max Magicka / Max Stamina
    - Health Recovery / Magicka Recovery / Stamina Recovery
    - Spell Damage / Weapon Damage
    - Spell Critical
    - Spell Critical Damage / Weapon Critical Damage
    - Spell Critical Healing / Weapon Critical Healing
    - Spell Resistance / Physical Resistance
    - Spell Penetration / Physical Penetration

NOTE: "Weapon Critical" is intentionally NOT implemented here. UESP's
equations.py references a ``WeaponCrit`` variable (e.g. in
``EffectiveWeaponPower`` / ``EffectivePower``) but never actually defines a
``WeaponCrit =`` formula anywhere in the reference file -- only ``SpellCrit``
is defined. Since the raw reference does not document this formula, adding
one here would mean guessing/assuming its shape, which violates the
"preserve exactly, do not add assumptions about missing inputs" requirement.
See the batch report for details.

Every function below takes already-resolved numeric contributions (i.e. the
caller has already figured out what each UESP source category -- Item, Set,
Skill, Skill2, Buff, CP, Mundus, Food, Attribute, Vampire, etc. -- evaluates
to for a given build). These functions do not know about ``Build`` or
``EffectResolver`` and are not wired into them.

Rounding note: UESP's reference text uses bare ``round(...)`` and
``floor(...)`` without specifying rounding-mode semantics (e.g. round-half-up
vs. round-half-to-even). This module uses Python's built-in ``round`` (banker's
rounding) and ``math.floor`` as the literal, unmodified translation of those
calls. This is flagged as an ambiguity rather than silently "corrected".

"Bloodthirsty" note: per instructions, Bloodthirsty contributions (already
computed elsewhere in equations.py as ``BloodthirstySpellDamage`` /
``BloodthirstyWeaponDamage``) are preserved here as a separate additive
term/parameter, exactly as UESP documents them, rather than folded into any
other input.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Max Health / Max Magicka / Max Stamina
# ---------------------------------------------------------------------------


def calculate_max_health(
    level: float,
    attribute_health: float,
    item_health: float,
    set_health: float,
    food_health: float,
    skill2_health: float,
    mundus_health: float,
    skill_health: float,
    buff_health: float,
) -> float:
    """UESP: Health =
    (300 * Level + 1000 + 122 * Attribute.Health + Item.Health + Set.Health
     + Food.Health + Skill2.Health + Mundus.Health)
    * (1 + Skill.Health + Buff.Health)
    """
    base_health = (
        300 * level
        + 1000
        + 122 * attribute_health
        + item_health
        + set_health
        + food_health
        + skill2_health
        + mundus_health
    )
    percent_bonus_multiplier = 1 + skill_health + buff_health
    return base_health * percent_bonus_multiplier


def calculate_max_magicka(
    level: float,
    attribute_magicka: float,
    item_magicka: float,
    set_magicka: float,
    food_magicka: float,
    mundus_magicka: float,
    skill2_magicka: float,
    skill_magicka: float,
    buff_magicka: float,
) -> float:
    """UESP: Magicka =
    (220 * Level + 1000 + 111 * Attribute.Magicka + Item.Magicka + Set.Magicka
     + Food.Magicka + Mundus.Magicka + Skill2.Magicka)
    * (1 + Skill.Magicka + Buff.Magicka)
    """
    base_magicka = (
        220 * level
        + 1000
        + 111 * attribute_magicka
        + item_magicka
        + set_magicka
        + food_magicka
        + mundus_magicka
        + skill2_magicka
    )
    percent_bonus_multiplier = 1 + skill_magicka + buff_magicka
    return base_magicka * percent_bonus_multiplier


def calculate_max_stamina(
    level: float,
    attribute_stamina: float,
    item_stamina: float,
    set_stamina: float,
    food_stamina: float,
    mundus_stamina: float,
    skill2_stamina: float,
    skill_stamina: float,
    buff_stamina: float,
) -> float:
    """UESP: Stamina =
    (220 * Level + 1000 + 111 * Attribute.Stamina + Item.Stamina + Set.Stamina
     + Food.Stamina + Mundus.Stamina + Skill2.Stamina)
    * (1 + Skill.Stamina + Buff.Stamina)
    """
    base_stamina = (
        220 * level
        + 1000
        + 111 * attribute_stamina
        + item_stamina
        + set_stamina
        + food_stamina
        + mundus_stamina
        + skill2_stamina
    )
    percent_bonus_multiplier = 1 + skill_stamina + buff_stamina
    return base_stamina * percent_bonus_multiplier


# ---------------------------------------------------------------------------
# Health / Magicka / Stamina Recovery
# ---------------------------------------------------------------------------


def calculate_health_recovery(
    level: float,
    item_health_regen: float,
    set_health_regen: float,
    set_health_regen_resist_factor: float,
    physical_resistance: float,
    spell_resistance: float,
    mundus_health_regen: float,
    food_health_regen: float,
    skill2_health_regen: float,
    cp_health_regen: float,
    skill_health_regen: float,
    buff_health_regen: float,
    vampire_health_regen: float,
) -> float:
    """UESP: HealthRegen =
    (round(5.592 * Level + 29.4) + Item.HealthRegen + Set.HealthRegen
     + min(1320, floor(Set.HealthRegenResistFactor * (PhysicalResist + SpellResist)))
     + Mundus.HealthRegen
     + (Food.HealthRegen) * (1 / (1 + Skill2.HealthRegen)))
    * (1 + CP.HealthRegen + Skill.HealthRegen + Buff.HealthRegen)
    * (1 + Skill2.HealthRegen)
    * (1 + Vampire.HealthRegen)
    """
    base_level_regen = round(5.592 * level + 29.4)

    resistance_capped_bonus = min(
        1320,
        math.floor(set_health_regen_resist_factor * (physical_resistance + spell_resistance)),
    )

    food_regen_term = food_health_regen * (1 / (1 + skill2_health_regen))

    base_regen = (
        base_level_regen
        + item_health_regen
        + set_health_regen
        + resistance_capped_bonus
        + mundus_health_regen
        + food_regen_term
    )

    percent_bonus_multiplier = 1 + cp_health_regen + skill_health_regen + buff_health_regen
    skill2_multiplier = 1 + skill2_health_regen
    vampire_multiplier = 1 + vampire_health_regen

    return base_regen * percent_bonus_multiplier * skill2_multiplier * vampire_multiplier


def calculate_magicka_recovery(
    level: float,
    item_magicka_regen: float,
    set_magicka_regen: float,
    mundus_magicka_regen: float,
    food_magicka_regen: float,
    skill2_magicka_regen: float,
    cp_magicka_regen: float,
    skill_magicka_regen: float,
    buff_magicka_regen: float,
) -> float:
    """UESP: MagickaRegen =
    (round(9.30612 * Level + 48.7) + Item.MagickaRegen + Set.MagickaRegen
     + Mundus.MagickaRegen
     + (Food.MagickaRegen) * (1 / (1 + Skill2.MagickaRegen)))
    * (1 + CP.MagickaRegen + Skill.MagickaRegen + Buff.MagickaRegen)
    * (1 + Skill2.MagickaRegen)
    """
    base_level_regen = round(9.30612 * level + 48.7)

    food_regen_term = food_magicka_regen * (1 / (1 + skill2_magicka_regen))

    base_regen = (
        base_level_regen
        + item_magicka_regen
        + set_magicka_regen
        + mundus_magicka_regen
        + food_regen_term
    )

    percent_bonus_multiplier = 1 + cp_magicka_regen + skill_magicka_regen + buff_magicka_regen
    skill2_multiplier = 1 + skill2_magicka_regen

    return base_regen * percent_bonus_multiplier * skill2_multiplier


def calculate_stamina_recovery(
    level: float,
    item_stamina_regen: float,
    set_stamina_regen: float,
    mundus_stamina_regen: float,
    food_stamina_regen: float,
    skill2_stamina_regen: float,
    cp_stamina_regen: float,
    skill_stamina_regen: float,
    buff_stamina_regen: float,
) -> float:
    """UESP: StaminaRegen =
    (round(9.30612 * Level + 48.7) + Item.StaminaRegen + Set.StaminaRegen
     + Mundus.StaminaRegen
     + (Food.StaminaRegen) * (1 / (1 + Skill2.StaminaRegen)))
    * (1 + CP.StaminaRegen + Skill.StaminaRegen + Buff.StaminaRegen)
    * (1 + Skill2.StaminaRegen)
    """
    base_level_regen = round(9.30612 * level + 48.7)

    food_regen_term = food_stamina_regen * (1 / (1 + skill2_stamina_regen))

    base_regen = (
        base_level_regen
        + item_stamina_regen
        + set_stamina_regen
        + mundus_stamina_regen
        + food_regen_term
    )

    percent_bonus_multiplier = 1 + cp_stamina_regen + skill_stamina_regen + buff_stamina_regen
    skill2_multiplier = 1 + skill2_stamina_regen

    return base_regen * percent_bonus_multiplier * skill2_multiplier


# ---------------------------------------------------------------------------
# Spell Damage / Weapon Damage
# ---------------------------------------------------------------------------


def calculate_spell_damage(
    level: float,
    item_spell_damage: float,
    set_spell_damage: float,
    skill2_spell_damage: float,
    mundus_spell_damage: float,
    cp_spell_damage: float,
    skill_spell_damage: float,
    buff_spell_damage: float,
    bloodthirsty_spell_damage: float,
) -> float:
    """UESP: SpellDamage =
    (20 * Level + Item.SpellDamage + Set.SpellDamage + Skill2.SpellDamage
     + Mundus.SpellDamage + CP.SpellDamage)
    * (1 + Skill.SpellDamage + Buff.SpellDamage)
    + BloodthirstySpellDamage
    """
    base_spell_damage = (
        20 * level
        + item_spell_damage
        + set_spell_damage
        + skill2_spell_damage
        + mundus_spell_damage
        + cp_spell_damage
    )
    percent_bonus_multiplier = 1 + skill_spell_damage + buff_spell_damage

    return base_spell_damage * percent_bonus_multiplier + bloodthirsty_spell_damage


def calculate_weapon_damage(
    level: float,
    item_weapon_damage: float,
    set_weapon_damage: float,
    skill2_weapon_damage: float,
    mundus_weapon_damage: float,
    cp_weapon_damage: float,
    skill_weapon_damage: float,
    buff_weapon_damage: float,
    bloodthirsty_weapon_damage: float,
) -> float:
    """UESP: WeaponDamage =
    (20 * Level + Item.WeaponDamage + Set.WeaponDamage + Skill2.WeaponDamage
     + Mundus.WeaponDamage + CP.WeaponDamage)
    * (1 + Skill.WeaponDamage + Buff.WeaponDamage)
    + BloodthirstyWeaponDamage
    """
    base_weapon_damage = (
        20 * level
        + item_weapon_damage
        + set_weapon_damage
        + skill2_weapon_damage
        + mundus_weapon_damage
        + cp_weapon_damage
    )
    percent_bonus_multiplier = 1 + skill_weapon_damage + buff_weapon_damage

    return base_weapon_damage * percent_bonus_multiplier + bloodthirsty_weapon_damage


# ---------------------------------------------------------------------------
# Spell Critical
# ---------------------------------------------------------------------------


def calculate_spell_critical(
    set_spell_critical: float,
    skill2_spell_critical: float,
    buff_spell_critical: float,
    cp_spell_critical: float,
    mundus_spell_critical: float,
    effective_level: float,
    item_spell_critical: float,
    skill_spell_critical: float,
) -> float:
    """UESP: SpellCrit =
    (Set.SpellCrit + Skill2.SpellCrit + Buff.SpellCrit + CP.SpellCrit
     + Mundus.SpellCrit) * (1 / (2 * EffectiveLevel * (100 + EffectiveLevel)))
    + 0.10 + Item.SpellCrit + Skill.SpellCrit

    NOTE: ``EffectiveLevel`` is not itself defined anywhere in
    equations.py; it is treated here as a caller-supplied input, exactly as
    UESP references it, per "do not add assumptions about missing inputs".
    """
    critical_rating = (
        set_spell_critical
        + skill2_spell_critical
        + buff_spell_critical
        + cp_spell_critical
        + mundus_spell_critical
    )
    effective_level_conversion_factor = 1 / (2 * effective_level * (100 + effective_level))

    return (
        critical_rating * effective_level_conversion_factor
        + 0.10
        + item_spell_critical
        + skill_spell_critical
    )


# NOTE: "Weapon Critical" is not implemented. See module docstring above --
# equations.py never defines a ``WeaponCrit =`` formula, it only *references*
# ``WeaponCrit`` as an already-known value inside EffectiveWeaponPower /
# EffectivePower. There is nothing to convert without guessing.


# ---------------------------------------------------------------------------
# Spell / Weapon Critical Damage
# ---------------------------------------------------------------------------


def calculate_spell_critical_damage(
    cp_spell_critical_damage: float,
    skill_critical_damage: float,
    cp_critical_damage: float,
    mundus_critical_damage: float,
    set_critical_damage: float,
    item_critical_damage: float,
    buff_critical_damage: float,
    skill2_critical_damage: float,
) -> float:
    """UESP: SpellCritDamage =
    (CP.SpellCritDamage + Skill.CritDamage + CP.CritDamage + Mundus.CritDamage
     + Set.CritDamage + Item.CritDamage + Buff.CritDamage + 0.5)
    * (1 + Skill2.CritDamage)
    """
    critical_damage_sum = (
        cp_spell_critical_damage
        + skill_critical_damage
        + cp_critical_damage
        + mundus_critical_damage
        + set_critical_damage
        + item_critical_damage
        + buff_critical_damage
        + 0.5
    )
    return critical_damage_sum * (1 + skill2_critical_damage)


def calculate_weapon_critical_damage(
    cp_weapon_critical_damage: float,
    skill_critical_damage: float,
    cp_critical_damage: float,
    mundus_critical_damage: float,
    set_critical_damage: float,
    item_critical_damage: float,
    buff_critical_damage: float,
    skill2_critical_damage: float,
) -> float:
    """UESP: WeaponCritDamage =
    (CP.WeaponCritDamage + Skill.CritDamage + CP.CritDamage + Mundus.CritDamage
     + Set.CritDamage + Item.CritDamage + Buff.CritDamage + 0.5)
    * (1 + Skill2.CritDamage)
    """
    critical_damage_sum = (
        cp_weapon_critical_damage
        + skill_critical_damage
        + cp_critical_damage
        + mundus_critical_damage
        + set_critical_damage
        + item_critical_damage
        + buff_critical_damage
        + 0.5
    )
    return critical_damage_sum * (1 + skill2_critical_damage)


# ---------------------------------------------------------------------------
# Spell / Weapon Critical Healing
# ---------------------------------------------------------------------------


def calculate_spell_critical_healing(
    cp_spell_critical_healing: float,
    skill_critical_healing: float,
    cp_critical_healing: float,
    mundus_critical_healing: float,
    set_critical_healing: float,
    item_critical_healing: float,
    buff_critical_healing: float,
    skill2_critical_healing: float,
) -> float:
    """UESP: SpellCritHealing =
    (CP.SpellCritHealing + Skill.CritHealing + CP.CritHealing
     + Mundus.CritHealing + Set.CritHealing + Item.CritHealing
     + Buff.CritHealing + 0.5) * (1 + Skill2.CritHealing)
    """
    critical_healing_sum = (
        cp_spell_critical_healing
        + skill_critical_healing
        + cp_critical_healing
        + mundus_critical_healing
        + set_critical_healing
        + item_critical_healing
        + buff_critical_healing
        + 0.5
    )
    return critical_healing_sum * (1 + skill2_critical_healing)


def calculate_weapon_critical_healing(
    cp_weapon_critical_healing: float,
    skill_critical_healing: float,
    cp_critical_healing: float,
    mundus_critical_healing: float,
    set_critical_healing: float,
    item_critical_healing: float,
    buff_critical_healing: float,
    skill2_critical_healing: float,
) -> float:
    """UESP: WeaponCritHealing =
    (CP.WeaponCritHealing + Skill.CritHealing + CP.CritHealing
     + Mundus.CritHealing + Set.CritHealing + Item.CritHealing
     + Buff.CritHealing + 0.5) * (1 + Skill2.CritHealing)
    """
    critical_healing_sum = (
        cp_weapon_critical_healing
        + skill_critical_healing
        + cp_critical_healing
        + mundus_critical_healing
        + set_critical_healing
        + item_critical_healing
        + buff_critical_healing
        + 0.5
    )
    return critical_healing_sum * (1 + skill2_critical_healing)


# ---------------------------------------------------------------------------
# Spell Resistance / Physical Resistance
# ---------------------------------------------------------------------------


def calculate_spell_resistance(
    item_spell_resist: float,
    skill2_spell_resist: float,
    mundus_spell_resist: float,
    set_spell_resist: float,
    skill_spell_resist: float,
    cp_spell_resist: float,
    buff_spell_resist: float,
) -> float:
    """UESP: SpellResist =
    (Item.SpellResist + Skill2.SpellResist + Mundus.SpellResist
     + Set.SpellResist + Skill.SpellResist + CP.SpellResist)
    * (1 + Buff.SpellResist)
    """
    base_spell_resist = (
        item_spell_resist
        + skill2_spell_resist
        + mundus_spell_resist
        + set_spell_resist
        + skill_spell_resist
        + cp_spell_resist
    )
    return base_spell_resist * (1 + buff_spell_resist)


def calculate_physical_resistance(
    item_physical_resist: float,
    skill2_physical_resist: float,
    mundus_physical_resist: float,
    set_physical_resist: float,
    skill_physical_resist: float,
    cp_physical_resist: float,
    buff_physical_resist: float,
) -> float:
    """UESP: PhysicalResist =
    (Item.PhysicalResist + Skill2.PhysicalResist + Mundus.PhysicalResist
     + Set.PhysicalResist + Skill.PhysicalResist + CP.PhysicalResist)
    * (1 + Buff.PhysicalResist)
    """
    base_physical_resist = (
        item_physical_resist
        + skill2_physical_resist
        + mundus_physical_resist
        + set_physical_resist
        + skill_physical_resist
        + cp_physical_resist
    )
    return base_physical_resist * (1 + buff_physical_resist)


# ---------------------------------------------------------------------------
# Spell Penetration / Physical Penetration
# ---------------------------------------------------------------------------


def calculate_spell_penetration(
    item_spell_penetration: float,
    set_spell_penetration: float,
    skill_spell_penetration: float,
    cp_spell_penetration: float,
    buff_spell_penetration: float,
    mundus_spell_penetration: float,
) -> float:
    """UESP: SpellPenetration =
    Item.SpellPenetration + Set.SpellPenetration + Skill.SpellPenetration
    + CP.SpellPenetration + Buff.SpellPenetration + Mundus.SpellPenetration
    """
    return (
        item_spell_penetration
        + set_spell_penetration
        + skill_spell_penetration
        + cp_spell_penetration
        + buff_spell_penetration
        + mundus_spell_penetration
    )


def calculate_physical_penetration(
    item_physical_penetration: float,
    set_physical_penetration: float,
    skill_physical_penetration: float,
    cp_physical_penetration: float,
    buff_physical_penetration: float,
    mundus_physical_penetration: float,
) -> float:
    """UESP: PhysicalPenetration =
    Item.PhysicalPenetration + Set.PhysicalPenetration
    + Skill.PhysicalPenetration + CP.PhysicalPenetration
    + Buff.PhysicalPenetration + Mundus.PhysicalPenetration
    """
    return (
        item_physical_penetration
        + set_physical_penetration
        + skill_physical_penetration
        + cp_physical_penetration
        + buff_physical_penetration
        + mundus_physical_penetration
    )