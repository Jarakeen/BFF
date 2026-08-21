"""Typed Python translations of UESP derived offensive-power formulas.

Source of truth: ``minmax/equations.py`` (do not edit that file).

This module converts ONLY the following formulas, exactly as documented:
    - Effective Spell Power
    - Effective Weapon Power
    - Effective Power

These are the next logical group after ``core_stats.py``: they are derived
offensive statistics that combine core stats (Magicka/Stamina, Spell/Weapon
Damage, Spell/Weapon Critical) with several OTHER formulas that have not
been translated yet (attack critical damage, attack mitigation, damage-done
modifiers, target damage-taken modifiers).

Per instructions, none of those not-yet-translated dependencies are wired
into ``Build`` or reconstructed here. Each is taken as an explicit,
clearly-named numeric parameter -- the caller supplies the already-resolved
value. This keeps the module a faithful, pure formula library rather than
prematurely assuming how those formulas or the Build/EffectResolver layer
will eventually supply them.

Untranslated dependencies treated as explicit numeric inputs in this batch:
    - SpellCrit            -> already translated (formulas.core_stats);
                               still just a plain parameter here, this
                               module does not call other formula functions.
    - WeaponCrit            -> NOT defined anywhere in equations.py (see the
                               note in formulas/core_stats.py). Kept as a
                               plain numeric parameter, exactly as UESP's
                               own EffectiveWeaponPower/EffectivePower
                               formulas reference it without defining it.
    - AttackSpellCritDamage  -> formula exists in equations.py
                               (AttackSpellCritDamage = SpellCritDamage -
                               Target.CritResist*(0.035/250)) but is not part
                               of this translation batch.
    - AttackWeaponCritDamage -> formula exists in equations.py, not yet
                               translated.
    - AttackSpellMitigation  -> formula exists in equations.py, not yet
                               translated.
    - AttackPhysicalMitigation -> formula exists in equations.py, not yet
                               translated.
    - CP.MagicDamageDone / CP.PhysicalDamageDone -> raw per-source
                               contributions, not formulas themselves.
    - DamageDone             -> formula exists in equations.py, not yet
                               translated.
    - Target.DamageTaken     -> a target-side value (DamageTaken has its own
                               formula in equations.py keyed off the
                               attacker's target, not yet translated).

Rounding note: as in core_stats.py, UESP's bare ``round(...)`` calls have no
documented rounding-mode, so Python's built-in ``round`` (banker's rounding)
is used as the literal, unmodified translation.
"""

from __future__ import annotations


def calculate_effective_spell_power(
    magicka: float,
    spell_damage: float,
    spell_critical: float,
    attack_spell_critical_damage: float,
    cp_magic_damage_done: float,
    attack_spell_mitigation: float,
    target_damage_taken: float,
    damage_done: float,
) -> float:
    """UESP: EffectiveSpellPower =
    (round(Magicka/10.5) + SpellDamage)
    * (1 + SpellCrit * AttackSpellCritDamage)
    * (1 + CP.MagicDamageDone)
    * (1 - AttackSpellMitigation)
    * (1 + Target.DamageTaken)
    * (1 + DamageDone)
    """
    magicka_power_term = round(magicka / 10.5)
    base_power = magicka_power_term + spell_damage

    critical_multiplier = 1 + spell_critical * attack_spell_critical_damage
    magic_damage_done_multiplier = 1 + cp_magic_damage_done
    mitigation_multiplier = 1 - attack_spell_mitigation
    target_damage_taken_multiplier = 1 + target_damage_taken
    damage_done_multiplier = 1 + damage_done

    return (
        base_power
        * critical_multiplier
        * magic_damage_done_multiplier
        * mitigation_multiplier
        * target_damage_taken_multiplier
        * damage_done_multiplier
    )


def calculate_effective_weapon_power(
    stamina: float,
    weapon_damage: float,
    weapon_critical: float,
    attack_weapon_critical_damage: float,
    cp_physical_damage_done: float,
    attack_physical_mitigation: float,
    target_damage_taken: float,
    damage_done: float,
) -> float:
    """UESP: EffectiveWeaponPower =
    (round(Stamina/10.5) + WeaponDamage)
    * (1 + WeaponCrit * AttackWeaponCritDamage)
    * (1 + CP.PhysicalDamageDone)
    * (1 - AttackPhysicalMitigation)
    * (1 + Target.DamageTaken)
    * (1 + DamageDone)

    NOTE: ``WeaponCrit`` (weapon_critical) has no defined formula anywhere in
    equations.py -- only SpellCrit is defined there. It is treated purely as
    an explicit caller-supplied numeric input here, per "do not invent
    missing formulas".
    """
    stamina_power_term = round(stamina / 10.5)
    base_power = stamina_power_term + weapon_damage

    critical_multiplier = 1 + weapon_critical * attack_weapon_critical_damage
    physical_damage_done_multiplier = 1 + cp_physical_damage_done
    mitigation_multiplier = 1 - attack_physical_mitigation
    target_damage_taken_multiplier = 1 + target_damage_taken
    damage_done_multiplier = 1 + damage_done

    return (
        base_power
        * critical_multiplier
        * physical_damage_done_multiplier
        * mitigation_multiplier
        * target_damage_taken_multiplier
        * damage_done_multiplier
    )


def calculate_effective_power(
    magicka: float,
    stamina: float,
    spell_damage: float,
    weapon_damage: float,
    spell_critical: float,
    weapon_critical: float,
    attack_spell_critical_damage: float,
    attack_weapon_critical_damage: float,
    cp_magic_damage_done: float,
    cp_physical_damage_done: float,
    attack_spell_mitigation: float,
    attack_physical_mitigation: float,
    target_damage_taken: float,
    damage_done: float,
) -> float:
    """UESP: EffectivePower =
    (round(max(Magicka, Stamina)/10.5) + max(SpellDamage, WeaponDamage))
    * (1 + max(SpellCrit, WeaponCrit) * max(AttackSpellCritDamage, AttackWeaponCritDamage))
    * (1 + max(CP.MagicDamageDone, CP.PhysicalDamageDone))
    * (1 - max(AttackSpellMitigation, AttackPhysicalMitigation))
    * (1 + Target.DamageTaken)
    * (1 + DamageDone)

    NOTE: as with calculate_effective_weapon_power, ``weapon_critical`` has
    no defined UESP formula and is taken as a plain caller-supplied input.
    """
    resource_power_term = round(max(magicka, stamina) / 10.5)
    max_damage = max(spell_damage, weapon_damage)
    base_power = resource_power_term + max_damage

    max_critical_chance = max(spell_critical, weapon_critical)
    max_critical_damage = max(attack_spell_critical_damage, attack_weapon_critical_damage)
    critical_multiplier = 1 + max_critical_chance * max_critical_damage

    max_damage_done_by_source = max(cp_magic_damage_done, cp_physical_damage_done)
    damage_done_by_source_multiplier = 1 + max_damage_done_by_source

    max_mitigation = max(attack_spell_mitigation, attack_physical_mitigation)
    mitigation_multiplier = 1 - max_mitigation

    target_damage_taken_multiplier = 1 + target_damage_taken
    damage_done_multiplier = 1 + damage_done

    return (
        base_power
        * critical_multiplier
        * damage_done_by_source_multiplier
        * mitigation_multiplier
        * target_damage_taken_multiplier
        * damage_done_multiplier
    )
