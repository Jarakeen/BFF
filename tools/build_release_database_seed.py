from __future__ import annotations

"""Create a privacy-safe first-install/recovery eso.db from the live development DB.

The source database mixes canonical ESO/reference data with user-owned runtime state.
Release packaging must never ship that user state. This tool creates a consistent SQLite
backup, clears only explicitly owned user-state table families, resets their sequences,
and VACUUMs the copy so deleted content is not left in free pages.

The source database is opened read-only and is never modified.
"""

import argparse
from pathlib import Path
import sqlite3


_EXACT_USER_TABLES = frozenset(
    {
        "team",
        "team_member",
        "collectible_profile",
        "collectible_progress",
        "collectible_rumor_progress",
    }
)

_USER_TABLE_PREFIXES = (
    "roster_",
    "generated_roster_",
    "stickerbook_",
    "log_",
)


def _is_user_owned_table(name: str) -> bool:
    key = str(name or "").strip()
    return key in _EXACT_USER_TABLES or any(
        key.startswith(prefix) for prefix in _USER_TABLE_PREFIXES
    )


def user_owned_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return tuple(
        str(row[0])
        for row in rows
        if _is_user_owned_table(str(row[0]))
    )


def create_release_database_seed(source: Path, destination: Path) -> tuple[str, ...]:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source database not found: {source}")
    if source == destination:
        raise ValueError("Release database destination must differ from the live source database")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    source_uri = f"file:{source.as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)

    with sqlite3.connect(destination) as db:
        db.execute("PRAGMA foreign_keys = OFF")
        tables = user_owned_tables(db)
        for table in tables:
            escaped = table.replace('"', '""')
            db.execute(f'DELETE FROM "{escaped}"')

        sequence_exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
        ).fetchone()
        if sequence_exists:
            for table in tables:
                db.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))

        db.commit()
        db.execute("VACUUM")
        db.execute("PRAGMA optimize")

        for table in tables:
            escaped = table.replace('"', '""')
            count = int(db.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0])
            if count:
                raise RuntimeError(
                    f"Release database sanitization failed: {table} still contains {count} row(s)"
                )

    return tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    tables = create_release_database_seed(args.source, args.destination)
    print(f"release_seed={args.destination}")
    print(f"cleared_user_tables={len(tables)}")
    for table in tables:
        print(f"  {table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
