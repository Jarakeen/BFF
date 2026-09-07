from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import get_data_dir

_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _plain_text(value: object) -> str:
    text = _COLOR_TAG_RE.sub("", str(value or ""))
    return " ".join(text.split())


def main() -> int:
    database = get_data_dir() / "eso.db"
    if not database.is_file():
        print(f"Database not found: {database}")
        return 2

    with sqlite3.connect(database) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "skill" not in tables:
            print("skill table is unavailable")
            return 2

        columns = _columns(connection, "skill")
        select_columns = [name for name in ("id", "base_ability_id", "name", "class_type", "skill_line", "description", "is_passive") if name in columns]
        if "name" not in select_columns:
            print("skill.name is unavailable")
            return 2

        where_parts = ["LOWER(COALESCE(name, '')) LIKE '%mastery%'"]
        if "skill_line" in columns:
            where_parts.append("LOWER(COALESCE(skill_line, '')) LIKE '%mastery%'")
        if "description" in columns:
            where_parts.append("LOWER(COALESCE(description, '')) LIKE '%class mastery%'")

        rows = connection.execute(
            f"SELECT {', '.join(select_columns)} FROM skill WHERE "
            + " OR ".join(where_parts)
            + " ORDER BY COALESCE(class_type, ''), COALESCE(skill_line, ''), name"
            if "class_type" in columns and "skill_line" in columns
            else f"SELECT {', '.join(select_columns)} FROM skill WHERE " + " OR ".join(where_parts) + " ORDER BY name"
        ).fetchall()

    print("========================================")
    print(" EXTREME BUILD CLASS MASTERY DATA AUDIT")
    print("========================================")
    print(f"Database: {database}")
    print(f"Matching skill rows: {len(rows)}")
    print()

    if not rows:
        print("No Class Mastery-looking rows were found in the canonical skill table.")
        print("BFF must not score Class Mastery until those passives are imported or otherwise canonically resolved.")
        return 0

    print(" | ".join(select_columns))
    print("-" * 120)
    for row in rows:
        values = []
        for value in row:
            text = _plain_text(value)
            if len(text) > 120:
                text = text[:117] + "..."
            values.append(text)
        print(" | ".join(values))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
