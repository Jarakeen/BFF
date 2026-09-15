from __future__ import annotations

"""H1-specific relevance rules for conditional gear objective blockers.

The shared gear objective service must preserve conditional Weapon/Spell Damage
because those mechanics matter in general. MOST Actual Heal can prove a narrower
fact: damage-type ability scopes cannot modify a healing event. This service owns
that H1 contextual proof without weakening the shared gear model.
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
    }
)


@dataclass(frozen=True)
class ExtremeActualHealGearConditionRelevanceResult:
    objective_key: str
    h1_mechanic_complete: bool
    ignored_blockers: tuple[str, ...] = ()
    remaining_blockers: tuple[str, ...] = ()


class ExtremeActualHealGearConditionRelevanceService:
    """Contextualize shared gear blockers for an H1 healing event."""

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
            if objective in {"spell_damage", "weapon_damage"} and any(
                f"requires condition {scope}" in text
                for scope in _DAMAGE_ONLY_ABILITY_SCOPES
            ):
                ignored.append(text)
            else:
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
