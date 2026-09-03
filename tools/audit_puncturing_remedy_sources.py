from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}


def _print_rows(title: str, rows: list[tuple]) -> None:
    print(title)
    if not rows:
        print("  (none)")
        return
    for row in rows:
        print("  ", row)


def main() -> int:
    database = Path(DEFAULT_DATABASE)
    print("PUNCTURING REMEDY CANONICAL SOURCE AUDIT")
    print(f"Database: {database}")
    print()

    with sqlite3.connect(database) as db:
        if _table_exists(db, "gear_set"):
            rows = db.execute(
                "SELECT id,name,category,max_equip_count FROM gear_set "
                "WHERE lower(name) LIKE ? ORDER BY name",
                ("%puncturing%remedy%",),
            ).fetchall()
            _print_rows("gear_set", rows)
        else:
            _print_rows("gear_set", [])
        print()

        if _table_exists(db, "entity"):
            cols = _columns(db, "entity")
            select = [name for name in ("id", "entity_type", "name", "slug") if name in cols]
            rows = db.execute(
                f"SELECT {','.join(select)} FROM entity "
                "WHERE lower(name) LIKE ? ORDER BY name",
                ("%puncturing%remedy%",),
            ).fetchall()
            _print_rows("entity", rows)
        else:
            _print_rows("entity", [])
        print()

        if _table_exists(db, "entity_source"):
            cols = _columns(db, "entity_source")
            select = [
                name
                for name in (
                    "entity_id",
                    "source",
                    "source_entity_type",
                    "source_entity_id",
                    "source_url",
                    "retrieved_at",
                )
                if name in cols
            ]
            where = []
            params: list[object] = []
            if "entity_id" in cols:
                where.append("lower(entity_id) LIKE ?")
                params.append("%puncturing%remedy%")
            if "source_url" in cols:
                where.append("lower(coalesce(source_url,'')) LIKE ?")
                params.append("%puncturing%remedy%")
            rows = []
            if select and where:
                rows = db.execute(
                    f"SELECT {','.join(select)} FROM entity_source "
                    f"WHERE {' OR '.join(where)} ORDER BY entity_id, source",
                    params,
                ).fetchall()
            _print_rows("entity_source", rows)
        else:
            _print_rows("entity_source", [])
        print()

        relation_tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND (lower(name) LIKE '%relation%' OR lower(name) LIKE '%effect%') "
                "ORDER BY name"
            ).fetchall()
        ]
        print("candidate relation/effect tables")
        if not relation_tables:
            print("  (none)")
        else:
            for table in relation_tables:
                print(f"  - {table}: {', '.join(sorted(_columns(db, table)))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
