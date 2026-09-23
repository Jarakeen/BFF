from __future__ import annotations

"""Build a privacy-limited FoundryDock user database seed for a custom EXE.

This seed intentionally carries only raid-setup state:
- Personnel
- Teams and memberships
- Personnel assignments
- Saved Raid Plans

Achievement/collectible and other checklist progress is not copied.
"""

import argparse
import sqlite3
from pathlib import Path


KEEP_TABLES = (
    "roster_member",
    "team",
    "team_member",
    "roster_member_assignment",
    "raid_plan",
)


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = OFF")
    return db


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _copy_table(source: sqlite3.Connection, target: sqlite3.Connection, table: str) -> int:
    if not _table_exists(source, table):
        return 0
    schema = source.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if schema is None or not str(schema["sql"] or "").strip():
        return 0
    target.execute(str(schema["sql"]))

    columns = [
        str(row["name"])
        for row in source.execute(f'PRAGMA table_info("{table}")').fetchall()
    ]
    if not columns:
        return 0
    quoted = ", ".join(f'"{column}"' for column in columns)
    rows = source.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    if rows:
        placeholders = ", ".join("?" for _ in columns)
        target.executemany(
            f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
            [tuple(row[column] for column in columns) for row in rows],
        )
    return len(rows)


def build_seed(
    source_path: Path,
    destination_path: Path,
    *,
    plan_id: str | None = None,
) -> dict[str, int]:
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"FoundryDock user database not found: {source_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        destination_path.unlink()

    source = _connect(source_path)
    target = _connect(destination_path)
    counts: dict[str, int] = {}
    try:
        for table in KEEP_TABLES:
            counts[table] = _copy_table(source, target, table)

        if _table_exists(target, "raid_plan"):
            selected_plan_id = str(plan_id or "").strip()
            plan_rows = target.execute(
                "SELECT plan_id FROM raid_plan ORDER BY updated_at DESC, plan_id COLLATE NOCASE"
            ).fetchall()
            if selected_plan_id:
                exists = any(
                    str(row["plan_id"]).casefold() == selected_plan_id.casefold()
                    for row in plan_rows
                )
                if not exists:
                    raise ValueError(
                        f"requested Raid Plan is not present in the user database: {selected_plan_id}"
                    )
                target.execute(
                    "DELETE FROM raid_plan WHERE plan_id <> ? COLLATE NOCASE",
                    (selected_plan_id,),
                )
                counts["raid_plan"] = 1
            elif len(plan_rows) > 1:
                raise ValueError(
                    "multiple saved Raid Plans exist; provide --plan-id so the custom EXE "
                    "does not accidentally include unrelated plans"
                )

        target.execute("PRAGMA foreign_keys = ON")
        violations = target.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                "custom user database seed failed foreign-key validation: "
                + "; ".join(str(tuple(row)) for row in violations[:10])
            )
        target.commit()
    except Exception:
        target.rollback()
        target.close()
        source.close()
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        try:
            source.close()
        except Exception:
            pass
        try:
            target.close()
        except Exception:
            pass
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--plan-id", default="")
    args = parser.parse_args()

    counts = build_seed(
        args.source,
        args.destination,
        plan_id=args.plan_id or None,
    )
    print(f"Created custom FoundryDock user seed: {args.destination}")
    for table in KEEP_TABLES:
        print(f"{table}: {counts.get(table, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
