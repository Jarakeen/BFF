from __future__ import annotations

"""H1-specific relevance rules for conditional gear objective blockers.

The shared gear objective service must preserve conditional Weapon/Spell Damage
because those mechanics matter in general. Standing MOST Actual Heal can prove a
few narrower facts without weakening that shared model: damage-type and reviewed
offensive-weapon ability scopes cannot modify a healing event; some unmapped
bonuses explicitly scope their Weapon/Spell Damage to damaging attacks or enemy
output only; reviewed always-on power plus an H1-irrelevant companion mechanic may
be projected by the dedicated Extreme tradeoff resolver; reviewed pre-event gear
conditions may be admitted only when a separate H1 witness service constructs the
required setup; and the standing scenario itself satisfies ``standing_still``.
"""

from dataclasses import dataclass
import re

from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


_DAMAGE_ONLY_ABILITY_SCOPES = frozenset(
    {
        "ability_scope:flame_damage",
        "ability_scope:frost_damage",
        "ability_scope:shock_damage",
        "ability_scope:magic_damage",
        "ability_scope:poison_and_disease_damage",
        "ability_scope:physical_and_bleed_damage",
        "ability_scope:dual_wield",
        "ability_scope:two_handed",
        "ability_scope:bow",
        "ability_scope:destruction_staff",
        "ability_scope:one_hand_and_shield",
    }
)
_STANDING_H1_CONDITIONS = frozenset({"standing_still"})

_DAMAGE_ONLY_POWER_TEXT = (
    re.compile(r"weapon and spell damage to your damaging\s*abilities", re.IGNORECASE),
    re.compile(
        r"weapon and spell damage to your damage over time and ranged attacks.*"
        r"weapon and spell damage to your melee attacks",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"weapon and spell damage against enemies\b", re.IGNORECASE),
    re.compile(r"weapon and spell damage against your marked target\b", re.IGNORECASE),
    re.compile(
        r"weapon and spell damage for flame, shock, or frost damage",
        re.IGNORECASE,
    ),
    re.compile(
        r"weapon and spell damage to your one hand and shield abilities",
        re.IGNORECASE,
    ),
    re.compile(
        r"weapon and spell damage against targets who are at or below\s*25% health",
        re.IGNORECASE,
    ),
    re.compile(
        r"weapon and spell damage by\s*8-369 against enemies inflicted with a poison damage effect",
        re.IGNORECASE,
    ),
)

_REVIEWED_H1_POWER_TRADEOFF_TEXT = (
    re.compile(
        r"Talfyg's Treachery \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"Increases your Weapon and Spell Damage by\s+8-372\..*"
        r"Increases your damage taken from Flame and Fighter'?s Guild abilities by\s+5%",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Dreugh King Slayer \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"Gain Major Brutality and Sorcery at all times, increasing your Weapon and Spell Damage by\s*20%\..*"
        r"When you kill an enemy, you gain Major Expedition",
        re.IGNORECASE | re.DOTALL,
    ),
)

_REVIEWED_H1_PRECONDITION_TEXT = (
    re.compile(
        r"Blessing of High Isle \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"When you are healed while in combat, increase your Weapon and Spell Damage by\s*8-369\s+for\s+5 seconds",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Fledgling's Nest \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"Gryphon Nest.*"
        r"first time you or a group member leaves the Nest.*"
        r"Minor Courage.*"
        r"Weapon and Spell Damage by\s*215",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Phoenix Moth Theurge \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"Healing yourself or an ally grants the target Minor Courage and Minor Force for\s*10 seconds.*"
        r"Weapon and Spell Damage by\s*215",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Spell Power Cure \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"When you overheal yourself or an ally, you give the target Major Courage for\s*5 seconds.*"
        r"Weapon and Spell Damage by\s*430",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"Vestment of Olorime \(5\): active set bonus is not yet mechanic-mapped:.*"
        r"Casting abilities that leave an effect on the ground in combat will create a circle of might for\s*5 seconds.*"
        r"You and your group members in the circle gain Major Courage for\s*20 seconds.*"
        r"Weapon and Spell Damage by\s*430",
        re.IGNORECASE | re.DOTALL,
    ),
)


@dataclass(frozen=True)
class ExtremeActualHealGearConditionRelevanceResult:
    objective_key: str
    h1_mechanic_complete: bool
    ignored_blockers: tuple[str, ...] = ()
    remaining_blockers: tuple[str, ...] = ()


class ExtremeActualHealGearConditionRelevanceService:
    """Contextualize shared gear blockers for a standing H1 healing event."""

    @classmethod
    def review(
        cls,
        row: ExtremeGearSetObjectiveCandidate,
    ) -> ExtremeActualHealGearConditionRelevanceResult:
        objective = str(row.objective_key or "").strip().casefold()
        if not row.unresolved:
            return ExtremeActualHealGearConditionRelevanceResult(
                objective_key=objective,
                h1_mechanic_complete=True,
            )

        ignored: list[str] = []
        remaining: list[str] = []
        for blocker in row.unresolved:
            text = str(blocker)
            if objective in {"spell_damage", "weapon_damage"}:
                damage_only_scope = any(
                    f"requires condition {scope}" in text
                    for scope in _DAMAGE_ONLY_ABILITY_SCOPES
                )
                standing_proven = any(
                    f"requires condition {condition}" in text
                    for condition in _STANDING_H1_CONDITIONS
                )
                damage_only_text = any(pattern.search(text) for pattern in _DAMAGE_ONLY_POWER_TEXT)
                reviewed_tradeoff = any(
                    pattern.search(text) for pattern in _REVIEWED_H1_POWER_TRADEOFF_TEXT
                )
                reviewed_precondition = any(
                    pattern.search(text) for pattern in _REVIEWED_H1_PRECONDITION_TEXT
                )
                if (
                    damage_only_scope
                    or standing_proven
                    or damage_only_text
                    or reviewed_tradeoff
                    or reviewed_precondition
                ):
                    ignored.append(text)
                    continue
            remaining.append(text)

        return ExtremeActualHealGearConditionRelevanceResult(
            objective_key=objective,
            h1_mechanic_complete=not remaining,
            ignored_blockers=tuple(ignored),
            remaining_blockers=tuple(remaining),
        )


__all__ = [
    "ExtremeActualHealGearConditionRelevanceResult",
    "ExtremeActualHealGearConditionRelevanceService",
]
