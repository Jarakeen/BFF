from __future__ import annotations

import sqlite3
from pathlib import Path


class SkillLineRepository:
    """Resolve canonical skill-line and passive metadata from eso.db."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._skill_line_cache: dict[tuple[str, str], str | None] = {}

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        name = str(ability_name or "").strip()
        if not name or not self.database_path.exists():
            return None

        cache_key = (self._norm(name), self._norm(class_name))
        if cache_key in self._skill_line_cache:
            return self._skill_line_cache[cache_key]

        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}
            required = {"name", "skill_line"}
            if not required.issubset(columns):
                self._skill_line_cache[cache_key] = None
                return None

            clauses = ["LOWER(TRIM(name)) = LOWER(TRIM(?))"]
            params: list[str] = [name]
            if class_name.strip() and "class_type" in columns:
                clauses.append("LOWER(TRIM(COALESCE(class_type, ''))) = LOWER(TRIM(?))")
                params.append(class_name.strip())
            if "is_passive" in columns:
                clauses.append("COALESCE(is_passive, 0) = 0")

            rows = db.execute(
                f"""
                SELECT DISTINCT TRIM(COALESCE(skill_line, ''))
                FROM ability
                WHERE {' AND '.join(clauses)}
                  AND TRIM(COALESCE(skill_line, '')) <> ''
                ORDER BY 1
                """,
                params,
            ).fetchall()

        lines = [str(row[0]).strip() for row in rows if str(row[0] or "").strip()]
        result = lines[0] if len(lines) == 1 else None
        self._skill_line_cache[cache_key] = result
        return result

    def passive_max_rank(self, passive_name: str) -> int | None:
        """Return the highest canonical rank recorded for one player passive."""
        name = str(passive_name or "").strip()
        if not name or not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as db:
            skill_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()}
            rank_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()}
            if not {"id", "name", "is_passive"}.issubset(skill_columns):
                return None
            if not {"skill_id", "rank"}.issubset(rank_columns):
                return None
            row = db.execute(
                """
                SELECT MAX(sr.rank)
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND LOWER(TRIM(s.name)) = LOWER(TRIM(?))
                """,
                (name,),
            ).fetchone()

        if row is None or row[0] is None:
            return None
        try:
            value = int(row[0])
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None
