from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class AbilityEffectProviderReference:
    """Reviewed ability -> combat-effect relationship from canonical SQLite data.

    Numeric ESO ability ids deliberately do not participate in semantic identity here.
    ``ability_key`` is the canonical lower-snake-case identity used by FoundryDock;
    the display name is preserved separately for human-readable surfaces.
    """

    ability_key: str
    ability_name: str
    effect_name: str
    relationship: str
    weapon_type: str | None = None
    condition: str | None = None
    source: str | None = None
    confidence: str | None = None


class AbilityEffectProviderReferenceService:
    """Read-only access to reviewed ability -> combat-effect relationships."""

    REQUIRED_TABLES = frozenset({"ability", "combat_effect", "ability_combat_effect"})

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _fallback_key(name: str) -> str:
        cleaned = "".join(char if char.isalnum() else " " for char in str(name or ""))
        return "_".join(cleaned.casefold().split())

    def all(self) -> tuple[AbilityEffectProviderReference, ...]:
        if not self.database_path.exists():
            return ()

        uri = f"file:{self.database_path.as_posix()}?mode=ro"
        try:
            db = sqlite3.connect(uri, uri=True)
        except sqlite3.OperationalError:
            return ()

        db.row_factory = sqlite3.Row
        try:
            tables = {
                str(row["name"])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not self.REQUIRED_TABLES.issubset(tables):
                return ()

            rows = db.execute(
                """
                SELECT
                    a.name AS ability_name,
                    a.index_name AS ability_index_name,
                    ce.name AS effect_name,
                    ace.relationship AS relationship,
                    ace.weapon_type AS weapon_type,
                    ace.condition AS condition,
                    ace.source AS source,
                    ace.confidence AS confidence
                FROM ability_combat_effect AS ace
                JOIN ability AS a
                    ON a.id = ace.ability_id
                JOIN combat_effect AS ce
                    ON ce.id = ace.combat_effect_id
                WHERE a.name IS NOT NULL
                  AND ce.name IS NOT NULL
                ORDER BY
                    lower(ce.name),
                    lower(a.name),
                    lower(ace.relationship),
                    coalesce(lower(ace.weapon_type), ''),
                    coalesce(lower(ace.condition), '')
                """
            ).fetchall()
        finally:
            db.close()

        deduped: dict[
            tuple[str, str, str, str | None, str | None, str | None, str | None],
            AbilityEffectProviderReference,
        ] = {}
        for row in rows:
            ability_name = str(row["ability_name"] or "").strip()
            effect_name = str(row["effect_name"] or "").strip()
            relationship = str(row["relationship"] or "").strip()
            if not ability_name or not effect_name or not relationship:
                continue

            raw_key = str(row["ability_index_name"] or "").strip()
            ability_key = raw_key or self._fallback_key(ability_name)
            reference = AbilityEffectProviderReference(
                ability_key=ability_key,
                ability_name=ability_name,
                effect_name=effect_name,
                relationship=relationship,
                weapon_type=(str(row["weapon_type"]).strip() if row["weapon_type"] else None),
                condition=(str(row["condition"]).strip() if row["condition"] else None),
                source=(str(row["source"]).strip() if row["source"] else None),
                confidence=(str(row["confidence"]).strip() if row["confidence"] else None),
            )
            identity = (
                reference.ability_key,
                reference.effect_name.casefold(),
                reference.relationship.casefold(),
                reference.weapon_type,
                reference.condition,
                reference.source,
                reference.confidence,
            )
            deduped.setdefault(identity, reference)

        return tuple(deduped.values())

    def for_effect(self, effect_name: str) -> tuple[AbilityEffectProviderReference, ...]:
        wanted = str(effect_name or "").strip().casefold()
        if not wanted:
            return ()
        return tuple(row for row in self.all() if row.effect_name.casefold() == wanted)
