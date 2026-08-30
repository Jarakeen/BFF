from __future__ import annotations

import sqlite3
from pathlib import Path


class SkillLineRepository:
    """Resolve a saved active ability name to its canonical ESO skill line.

    The passive stat resolver uses this only to count slotted abilities by
    skill line. It deliberately does not infer passive ownership or apply any
    effect by itself.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        name = str(ability_name or "").strip()
        if not name or not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}
            required = {"name", "skill_line"}
            if not required.issubset(columns):
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
        if len(lines) != 1:
            return None
        return lines[0]
