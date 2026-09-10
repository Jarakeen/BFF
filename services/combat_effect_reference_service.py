from __future__ import annotations

"""Read-only reference projection for canonical combat-effect records."""

from dataclasses import dataclass
import sqlite3
from pathlib import Path

from engine.config import DEFAULT_DATABASE


@dataclass(frozen=True)
class CombatEffectTriggerReference:
    trigger_type: str
    damage_type: str | None
    weapon_requirement: str | None
    condition: str | None
    raw_source: str | None


@dataclass(frozen=True)
class CombatEffectInteractionReference:
    target_name: str
    interaction_type: str
    condition: str | None
    duration: float | None
    target_value: float | None
    target_unit: str | None
    target_scope: str | None
    raw_source: str | None


@dataclass(frozen=True)
class CombatEffectReference:
    effect_id: int
    name: str
    category: str
    description: str
    duration: float | None
    tick_interval: float | None
    stack_max: int | None
    immunity_duration: float | None
    raw_source: str | None
    triggers: tuple[CombatEffectTriggerReference, ...] = ()
    interactions: tuple[CombatEffectInteractionReference, ...] = ()


class CombatEffectReferenceService:
    """Expose imported combat-effect truth without mutating or reinterpreting it."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE):
        self.database_path = Path(database_path)

    def all(self) -> tuple[CombatEffectReference, ...]:
        if not self.database_path.exists():
            return ()

        connection = sqlite3.connect(self.database_path)
        try:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='combat_effect'"
            ).fetchone()
            if table is None:
                return ()

            effect_rows = connection.execute(
                """
                SELECT id, name, category, description, duration, tick_interval,
                       stack_max, immunity_duration, raw_source
                FROM combat_effect
                ORDER BY name COLLATE NOCASE, id
                """
            ).fetchall()

            trigger_rows = connection.execute(
                """
                SELECT combat_effect_id, trigger_type, damage_type,
                       weapon_requirement, condition, raw_source
                FROM combat_effect_trigger
                ORDER BY combat_effect_id, id
                """
            ).fetchall()

            interaction_rows = connection.execute(
                """
                SELECT source_effect_id, target_name, interaction_type, condition,
                       duration, target_value, target_unit, target_scope, raw_source
                FROM combat_effect_interaction
                ORDER BY source_effect_id, id
                """
            ).fetchall()
        finally:
            connection.close()

        triggers_by_effect: dict[int, list[CombatEffectTriggerReference]] = {}
        for effect_id, trigger_type, damage_type, weapon_requirement, condition, raw_source in trigger_rows:
            triggers_by_effect.setdefault(int(effect_id), []).append(
                CombatEffectTriggerReference(
                    trigger_type=str(trigger_type or ""),
                    damage_type=str(damage_type) if damage_type is not None else None,
                    weapon_requirement=(
                        str(weapon_requirement) if weapon_requirement is not None else None
                    ),
                    condition=str(condition) if condition is not None else None,
                    raw_source=str(raw_source) if raw_source is not None else None,
                )
            )

        interactions_by_effect: dict[int, list[CombatEffectInteractionReference]] = {}
        for (
            effect_id,
            target_name,
            interaction_type,
            condition,
            duration,
            target_value,
            target_unit,
            target_scope,
            raw_source,
        ) in interaction_rows:
            interactions_by_effect.setdefault(int(effect_id), []).append(
                CombatEffectInteractionReference(
                    target_name=str(target_name or ""),
                    interaction_type=str(interaction_type or ""),
                    condition=str(condition) if condition is not None else None,
                    duration=float(duration) if duration is not None else None,
                    target_value=float(target_value) if target_value is not None else None,
                    target_unit=str(target_unit) if target_unit is not None else None,
                    target_scope=str(target_scope) if target_scope is not None else None,
                    raw_source=str(raw_source) if raw_source is not None else None,
                )
            )

        return tuple(
            CombatEffectReference(
                effect_id=int(effect_id),
                name=str(name or ""),
                category=str(category or ""),
                description=str(description or ""),
                duration=float(duration) if duration is not None else None,
                tick_interval=float(tick_interval) if tick_interval is not None else None,
                stack_max=int(stack_max) if stack_max is not None else None,
                immunity_duration=(
                    float(immunity_duration) if immunity_duration is not None else None
                ),
                raw_source=str(raw_source) if raw_source is not None else None,
                triggers=tuple(triggers_by_effect.get(int(effect_id), ())),
                interactions=tuple(interactions_by_effect.get(int(effect_id), ())),
            )
            for (
                effect_id,
                name,
                category,
                description,
                duration,
                tick_interval,
                stack_max,
                immunity_duration,
                raw_source,
            ) in effect_rows
        )
