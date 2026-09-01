from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChampionPointSkillRelationship:
    champion_point_id: int
    champion_point_name: str
    skill_id: int
    skill_name: str
    relationship: str
    condition: str | None = None
    source: str | None = None
    confidence: str | None = None
    source_url: str | None = None
    raw_source: str | None = None


class ChampionPointSkillRepository:
    """Read explicit harvested ESO-Hub CP -> skill applicability.

    This repository is intentionally fail-closed. A missing table, missing row,
    or unlinked Champion Point never becomes inferred applicability. Component
    semantics may narrow an explicit relationship later, but may not invent one.
    """

    TABLE = "champion_point_skill"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return (
            db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone()
            is not None
        )

    @staticmethod
    def _columns(db: sqlite3.Connection, name: str) -> set[str]:
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({name})").fetchall()}

    def available(self) -> bool:
        if not self.database_path.exists():
            return False
        with sqlite3.connect(self.database_path) as db:
            return self._table_exists(db, self.TABLE)

    def get_for_skill_id(self, skill_id: int) -> tuple[ChampionPointSkillRelationship, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            if not self._table_exists(db, self.TABLE):
                return ()
            if not self._table_exists(db, "champion_point") or not self._table_exists(db, "skill"):
                return ()

            columns = self._columns(db, self.TABLE)
            condition = "cps.condition" if "condition" in columns else "NULL"
            source_url = "cps.source_url" if "source_url" in columns else "NULL"
            rows = db.execute(
                f"""
                SELECT
                    cps.champion_point_id,
                    cp.name AS champion_point_name,
                    cps.skill_id,
                    s.name AS skill_name,
                    cps.relationship,
                    {condition} AS condition,
                    cps.source,
                    cps.confidence,
                    {source_url} AS source_url,
                    cps.raw_source
                FROM champion_point_skill cps
                JOIN champion_point cp ON cp.id = cps.champion_point_id
                JOIN skill s ON s.id = cps.skill_id
                WHERE cps.skill_id = ?
                ORDER BY LOWER(cp.name), cps.champion_point_id
                """,
                (int(skill_id),),
            ).fetchall()

        return tuple(
            ChampionPointSkillRelationship(
                champion_point_id=int(row["champion_point_id"]),
                champion_point_name=str(row["champion_point_name"] or "").strip(),
                skill_id=int(row["skill_id"]),
                skill_name=str(row["skill_name"] or "").strip(),
                relationship=str(row["relationship"] or "").strip(),
                condition=(str(row["condition"]).strip() if row["condition"] is not None else None),
                source=(str(row["source"]).strip() if row["source"] is not None else None),
                confidence=(str(row["confidence"]).strip() if row["confidence"] is not None else None),
                source_url=(str(row["source_url"]).strip() if row["source_url"] is not None else None),
                raw_source=(str(row["raw_source"]).strip() if row["raw_source"] is not None else None),
            )
            for row in rows
        )

    def get_for_skill_rank(self, skill_rank_id: int) -> tuple[ChampionPointSkillRelationship, ...]:
        if not self.database_path.exists():
            return ()
        with sqlite3.connect(self.database_path) as db:
            if not self._table_exists(db, "skill_rank"):
                return ()
            row = db.execute(
                "SELECT skill_id FROM skill_rank WHERE id = ?",
                (int(skill_rank_id),),
            ).fetchone()
        if row is None:
            return ()
        return self.get_for_skill_id(int(row[0]))

    def find(
        self,
        *,
        skill_id: int,
        champion_point_name: str,
    ) -> ChampionPointSkillRelationship | None:
        requested = str(champion_point_name or "").strip().casefold()
        if not requested:
            return None
        for relationship in self.get_for_skill_id(skill_id):
            if relationship.champion_point_name.casefold() == requested:
                return relationship
        return None

    def explicitly_applies(self, *, skill_id: int, champion_point_name: str) -> bool:
        return self.find(
            skill_id=skill_id,
            champion_point_name=champion_point_name,
        ) is not None
