from __future__ import annotations

from dataclasses import dataclass

from .combat_effect_semantics import GameUpdate, normalize_game_update
from .named_combat_buffs import canonical_buff_name


@dataclass(frozen=True)
class CombatState:
    """Explicit transient combat conditions for one calculation snapshot.

    Static build math must not infer these conditions from selected gear, skills,
    potions, or Champion Points. Callers opt into combat-state effects
    deliberately. Named buffs are canonicalized and deduplicated at the state
    boundary so downstream resolvers do not need to guess aliases.

    ``game_update`` versions the meaning of those named effects. U50 remains the
    default until Update 51 is live; callers may explicitly evaluate U51/PTS
    semantics without rewriting historical source data.
    """

    in_combat: bool = False
    active_buffs: tuple[str, ...] = ()
    game_update: GameUpdate | str = GameUpdate.U50

    def __post_init__(self) -> None:
        object.__setattr__(self, "game_update", normalize_game_update(self.game_update))
        seen: set[str] = set()
        normalized: list[str] = []
        for value in self.active_buffs:
            canonical = canonical_buff_name(value)
            if canonical is None:
                name = " ".join(str(value or "").strip().split())
                if not name:
                    continue
                canonical = name
            key = canonical.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(canonical)
        object.__setattr__(self, "active_buffs", tuple(normalized))

    def has_buff(self, name: str) -> bool:
        requested = " ".join(str(name or "").strip().casefold().split())
        return bool(requested) and any(buff.casefold() == requested for buff in self.active_buffs)


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
