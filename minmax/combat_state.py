from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CombatState:
    """Explicit transient combat conditions for one calculation snapshot.

    Static build math must not infer these conditions from selected gear, skills,
    or Champion Points. Callers opt into combat-state effects deliberately.
    """

    in_combat: bool = False


@dataclass(frozen=True)
class IncomingAttackState:
    """Explicit properties of the incoming hit currently being evaluated.

    Damage-family-specific defenses must not leak into the generic standing
    character sheet. Callers identify the hit family when they need a contextual
    mitigation result.
    """

    is_ranged: bool = False
    is_projectile: bool = False

    @property
    def qualifies_for_deflect_bolts(self) -> bool:
        return self.is_ranged or self.is_projectile


@dataclass(frozen=True)
class LightAttackState:
    """Resolved inputs required by the staff light-attack formulas."""

    # Core stats
    magicka: float
    stamina: float

    # Derived light-attack power
    la_flame_spell_damage: float = 0.0
    la_flame_weapon_damage: float = 0.0
    la_frost_spell_damage: float = 0.0
    la_frost_weapon_damage: float = 0.0
    la_shock_spell_damage: float = 0.0
    la_shock_weapon_damage: float = 0.0

    # Light-attack modifiers
    skill2_la_damage: float = 0.0
    cp_la_damage: float = 0.0
    skill_la_damage: float = 0.0
    set_la_damage: float = 0.0

    # Heavy-attack modifiers referenced by Shock Staff LA
    skill_ha_damage: float = 0.0
    set_ha_damage: float = 0.0

    # Buffs
    buff_empower: float = 0.0

    # Damage Done modifiers
    flame_damage_done: float = 0.0
    frost_damage_done: float = 0.0
    shock_damage_done: float = 0.0
    direct_damage_done: float = 0.0
    single_target_damage_done: float = 0.0
    dot_damage_done: float = 0.0
    damage_done: float = 0.0
