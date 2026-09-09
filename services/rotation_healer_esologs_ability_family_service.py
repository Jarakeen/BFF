from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class RotationHealerEsoLogsAbilityFamily:
    source_name: str
    skill_id: int
    ability_game_ids: tuple[int, ...]
    evidence: tuple[str, ...]

    def contains(self, ability_game_id: int | None) -> bool:
        return ability_game_id is not None and int(ability_game_id) in self.ability_game_ids


class RotationHealerEsoLogsAbilityFamilyService:
    """Resolve all canonical rank ability ids for one named skill family.

    ESO Logs evidence may use a different rank/member ability id than the exact
    max-rank id selected by the rotation engine. This service keeps identity
    matching inside the canonical ``skill``/``skill_rank`` family instead of
    treating one ability id as the whole skill.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def resolve(self, source_name: str) -> RotationHealerEsoLogsAbilityFamily | None:
        requested = str(source_name).strip()
        if not requested or not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"skill", "skill_rank"}.issubset(tables):
                return None

            rows = connection.execute(
                """
                SELECT DISTINCT
                       s.id AS skill_id,
                       sr.ability_id AS ability_id,
                       COALESCE(NULLIF(sr.raw_name, ''), NULLIF(s.name, ''), '') AS resolved_name
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                WHERE lower(COALESCE(NULLIF(sr.raw_name, ''), NULLIF(s.name, ''), '')) = lower(?)
                   OR lower(COALESCE(NULLIF(s.name, ''), '')) = lower(?)
                ORDER BY s.id, sr.ability_id
                """,
                (requested, requested),
            ).fetchall()
            if not rows:
                return None

            skill_ids = sorted({int(row["skill_id"]) for row in rows})
            if len(skill_ids) != 1:
                return None
            skill_id = skill_ids[0]

            family_rows = connection.execute(
                """
                SELECT DISTINCT ability_id
                FROM skill_rank
                WHERE skill_id = ?
                  AND ability_id IS NOT NULL
                ORDER BY ability_id
                """,
                (skill_id,),
            ).fetchall()
            ids = tuple(int(row["ability_id"]) for row in family_rows)
            if not ids:
                return None

            return RotationHealerEsoLogsAbilityFamily(
                source_name=requested,
                skill_id=skill_id,
                ability_game_ids=ids,
                evidence=(
                    f"canonical skill id {skill_id}",
                    "all persisted skill_rank ability ids for that canonical skill family",
                ),
            )
