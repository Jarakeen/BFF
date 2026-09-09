from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class RotationHealerEsoLogsCanonicalSkillAliases:
    canonical_skill_id: str
    ability_game_ids: tuple[int, ...]
    evidence: tuple[str, ...]

    def contains(self, ability_game_id: int | None) -> bool:
        return ability_game_id is not None and int(ability_game_id) in self.ability_game_ids


class RotationHealerEsoLogsCanonicalSkillAliasService:
    """Resolve numeric ESO ability aliases for a canonical lower-snake-case skill id.

    Canonical identity is the persisted string id (for example
    ``radiating_regeneration``). Numeric ability ids are evidence aliases only;
    they never determine semantic identity by themselves.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def resolve(self, canonical_skill_id: str) -> RotationHealerEsoLogsCanonicalSkillAliases | None:
        key = str(canonical_skill_id).strip().lower()
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
                SELECT DISTINCT ability_id
                FROM ability
                WHERE lower(COALESCE(index_name, '')) = ?
                  AND ability_id IS NOT NULL
                ORDER BY ability_id
                """,
                (key,),
            ).fetchall()
            ids = tuple(int(row["ability_id"]) for row in rows)
            if not ids:
                return None

            return RotationHealerEsoLogsCanonicalSkillAliases(
                canonical_skill_id=key,
                ability_game_ids=ids,
                evidence=(
                    f"canonical skill id {key}",
                    "numeric aliases resolved only from ability.index_name",
                    "ability ids are observational aliases, not canonical identity",
                ),
            )
