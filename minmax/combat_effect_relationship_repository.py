import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CombatEffectTriggerRecord:
    """
    How a named combat effect (e.g. "Chilled") actually gets applied in
    the first place, per the `combat_effect_trigger` table populated by
    importers.combat_effect_importer.CombatEffectImporter.

    `damage_type`/`weapon_requirement` describe a damage or weapon
    prerequisite, not another named effect - that is a different shape
    of fact than an interaction (see CombatEffectInteractionRecord) and
    is exposed as-is rather than forced into the EffectRelationship
    model, which connects one named effect identity to another.
    """

    effect_name: str
    trigger_type: str
    damage_type: str | None
    weapon_requirement: str | None
    condition: str | None
    raw_source: str | None


@dataclass(frozen=True)
class CombatEffectInteractionRecord:
    """
    What a named combat effect causes or enables, per the
    `combat_effect_interaction` table populated by the same importer.

    `source_effect_name` and `target_name` are both named-effect
    identities (e.g. "Chilled" -> "Minor Brittle"), which is exactly the
    shape EffectRelationship expects - see
    `character_build.combat_effect_relationship_bridge` for the generic
    converter.
    """

    source_effect_name: str
    target_name: str
    interaction_type: str
    condition: str | None
    duration: float | None
    target_value: float | None
    target_unit: str | None
    target_scope: str | None
    raw_source: str | None


class CombatEffectRelationshipRepository:
    """
    Reads the generic `combat_effect` / `combat_effect_trigger` /
    `combat_effect_interaction` tables.

    This repository is deliberately generic: it does not know about
    "Chilled" or "Minor Brittle" specifically, only about the schema
    those tables share for ANY combat effect the importer has recorded.
    New effects/relationships become available to callers the moment
    they are added to the importer's data, with no code change here.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_triggers(
        self,
        effect_name: str | None = None,
    ) -> tuple[CombatEffectTriggerRecord, ...]:
        query = """
            SELECT
                ce.name,
                t.trigger_type,
                t.damage_type,
                t.weapon_requirement,
                t.condition,
                t.raw_source
            FROM combat_effect_trigger t
            JOIN combat_effect ce ON ce.id = t.combat_effect_id
            {where}
            ORDER BY t.id
        """
        where = "WHERE ce.name = ?" if effect_name is not None else ""
        params: tuple = (effect_name,) if effect_name is not None else ()

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(query.format(where=where), params).fetchall()

        return tuple(CombatEffectTriggerRecord(*row) for row in rows)

    def get_interactions(
        self,
        source_effect_name: str | None = None,
    ) -> tuple[CombatEffectInteractionRecord, ...]:
        query = """
            SELECT
                ce.name,
                i.target_name,
                i.interaction_type,
                i.condition,
                i.duration,
                i.target_value,
                i.target_unit,
                i.target_scope,
                i.raw_source
            FROM combat_effect_interaction i
            JOIN combat_effect ce ON ce.id = i.source_effect_id
            {where}
            ORDER BY i.id
        """
        where = "WHERE ce.name = ?" if source_effect_name is not None else ""
        params: tuple = (source_effect_name,) if source_effect_name is not None else ()

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(query.format(where=where), params).fetchall()

        return tuple(CombatEffectInteractionRecord(*row) for row in rows)
