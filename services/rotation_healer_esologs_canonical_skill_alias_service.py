from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


@dataclass(frozen=True)
class RotationHealerEsoLogsCanonicalSkillAliases:
    canonical_skill_id: str
    ability_game_ids: tuple[int, ...]
    evidence: tuple[str, ...]

    def contains(self, ability_game_id: int | None) -> bool:
        return ability_game_id is not None and int(ability_game_id) in self.ability_game_ids


def _canonical_skill_id(value: object) -> str:
    """Normalize imported/display skill names to canonical lower-snake-case ids."""

    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


class RotationHealerEsoLogsCanonicalSkillAliasService:
    """Resolve numeric ESO ability aliases for a canonical lower-snake-case skill id.

    Canonical identity is the persisted string id (for example
    ``radiating_regeneration``). Numeric ability ids are evidence aliases only;
    they never determine semantic identity by themselves.

    Imported ``ability.index_name`` values may use display-style whitespace and
    punctuation. They are normalized to the same semantic lower-snake-case form
    before comparison rather than requiring their storage representation to match
    canonical ids byte-for-byte.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def resolve(self, canonical_skill_id: str) -> RotationHealerEsoLogsCanonicalSkillAliases | None:
        key = _canonical_skill_id(canonical_skill_id)
        if not key or not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "ability" not in tables:
                return None

            ability_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(ability)").fetchall()
            }
            if not {"ability_id", "index_name"}.issubset(ability_columns):
                return None

            rows = connection.execute(
                """
                SELECT DISTINCT ability_id, index_name
                FROM ability
                WHERE ability_id IS NOT NULL
                  AND TRIM(COALESCE(index_name, '')) <> ''
                ORDER BY ability_id
                """
            ).fetchall()
            ids = tuple(
                int(row["ability_id"])
                for row in rows
                if _canonical_skill_id(row["index_name"]) == key
            )
            if not ids:
                return None

            return RotationHealerEsoLogsCanonicalSkillAliases(
                canonical_skill_id=key,
                ability_game_ids=ids,
                evidence=(
                    f"canonical skill id {key}",
                    "numeric aliases resolved from semantically normalized ability.index_name",
                    "ability ids are observational aliases, not canonical identity",
                ),
            )
