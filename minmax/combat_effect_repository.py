import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CombatEffectTriggerRecord:
    """How a canonical combat effect (e.g. Chilled) gets applied."""

    trigger_type: str
    damage_type: str | None
    weapon_requirement: str | None
    condition: str | None


@dataclass(frozen=True)
class CombatEffectInteractionRecord:
    """Something a canonical combat effect causes/enables (e.g. Chilled -> Minor Brittle)."""

    target_name: str
    interaction_type: str
    condition: str | None
    duration: float | None
    value: float | None
    unit: str | None
    scope: str | None


@dataclass(frozen=True)
class CombatEffectRecord:
    """
    A canonical ESO combat/status effect (e.g. Chilled, Off Balance),
    together with how it is triggered and what it causes.
    """

    name: str
    category: str
    description: str | None
    duration: float | None
    tick_interval: float | None
    stack_max: int | None
    immunity_duration: float | None
    triggers: tuple[CombatEffectTriggerRecord, ...]
    interactions: tuple[CombatEffectInteractionRecord, ...]


class CombatEffectRepository:
    """
    Loads the ESO database's canonical combat_effect catalog: status
    effects such as Chilled and Burning, and the combat_effect_trigger /
    combat_effect_interaction rows that describe how they are applied and
    what they cause (e.g. Chilled -> Minor Brittle while an Ice Staff is
    active).

    This is the game's baseline status-effect mechanics, independent of
    any specific build - a future task connects specific
    abilities/enchantments to these statuses via the ability_combat_effect
    table.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_all(self) -> list[CombatEffectRecord]:
        with sqlite3.connect(self.database_path) as connection:
            effect_rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    description,
                    duration,
                    tick_interval,
                    stack_max,
                    immunity_duration
                FROM combat_effect
                ORDER BY id
                """
            ).fetchall()

            records: list[CombatEffectRecord] = []

            for (
                effect_id,
                name,
                category,
                description,
                duration,
                tick_interval,
                stack_max,
                immunity_duration,
            ) in effect_rows:
                triggers = self._get_triggers(connection, effect_id)
                interactions = self._get_interactions(connection, effect_id)

                records.append(
                    CombatEffectRecord(
                        name=name,
                        category=category,
                        description=description,
                        duration=duration,
                        tick_interval=tick_interval,
                        stack_max=stack_max,
                        immunity_duration=immunity_duration,
                        triggers=triggers,
                        interactions=interactions,
                    )
                )

            return records

    def _get_triggers(
        self,
        connection: sqlite3.Connection,
        effect_id: int,
    ) -> tuple[CombatEffectTriggerRecord, ...]:
        rows = connection.execute(
            """
            SELECT
                trigger_type,
                damage_type,
                weapon_requirement,
                condition
            FROM combat_effect_trigger
            WHERE combat_effect_id = ?
            ORDER BY id
            """,
            (effect_id,),
        ).fetchall()

        return tuple(
            CombatEffectTriggerRecord(
                trigger_type=trigger_type,
                damage_type=damage_type,
                weapon_requirement=weapon_requirement,
                condition=condition,
            )
            for (
                trigger_type,
                damage_type,
                weapon_requirement,
                condition,
            ) in rows
        )

    def _get_interactions(
        self,
        connection: sqlite3.Connection,
        effect_id: int,
    ) -> tuple[CombatEffectInteractionRecord, ...]:
        rows = connection.execute(
            """
            SELECT
                target_name,
                interaction_type,
                condition,
                duration,
                target_value,
                target_unit,
                target_scope
            FROM combat_effect_interaction
            WHERE source_effect_id = ?
            ORDER BY id
            """,
            (effect_id,),
        ).fetchall()

        return tuple(
            CombatEffectInteractionRecord(
                target_name=target_name,
                interaction_type=interaction_type,
                condition=condition,
                duration=duration,
                value=value,
                unit=unit,
                scope=scope,
            )
            for (
                target_name,
                interaction_type,
                condition,
                duration,
                value,
                unit,
                scope,
            ) in rows
        )
