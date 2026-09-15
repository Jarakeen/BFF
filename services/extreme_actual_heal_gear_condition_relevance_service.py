from __future__ import annotations

"""H1-specific relevance rules for conditional gear objective blockers.

The shared gear objective service must preserve conditional Weapon/Spell Damage
because those mechanics matter in general. Standing MOST Actual Heal can prove a
few narrower facts without weakening that shared model: damage-type and reviewed
offensive-weapon ability scopes cannot modify a healing event, and the standing
scenario itself satisfies a ``standing_still`` condition.
"""

from dataclasses import dataclass

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
                damage_only = any(
                    f"requires condition {scope}" in text
                    for scope in _DAMAGE_ONLY_ABILITY_SCOPES
                )
                standing_proven = any(
                    f"requires condition {condition}" in text
                    for condition in _STANDING_H1_CONDITIONS
                )
                if damage_only or standing_proven:
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
