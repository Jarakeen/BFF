"""
Black Feather Foundry
Racial Database Schema

Adds the racial-data domain to data/eso.db.

Tables:
    race
    race_stat
    race_bonus

This is a schema migration only.
It does NOT import racial_data.json.

Run from the FoundryDock root:

    python .\database\create_racial_schema.py

The migration is idempotent. Running it again will not destroy
existing data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "eso.db"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS race (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    alliance TEXT,
    association TEXT
);

CREATE TABLE IF NOT EXISTS race_stat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    stat TEXT NOT NULL,
    value INTEGER NOT NULL,

    FOREIGN KEY (race_id)
        REFERENCES race(id)
        ON DELETE CASCADE,

    UNIQUE (race_id, stat)
);

CREATE INDEX IF NOT EXISTS idx_race_stat_race_id
    ON race_stat(race_id);

CREATE INDEX IF NOT EXISTS idx_race_stat_stat
    ON race_stat(stat);

CREATE TABLE IF NOT EXISTS race_bonus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    bonus_text TEXT NOT NULL,
    source TEXT,

    FOREIGN KEY (race_id)
        REFERENCES race(id)
        ON DELETE CASCADE,

    UNIQUE (race_id, bonus_text)
);

CREATE INDEX IF NOT EXISTS idx_race_bonus_race_id
    ON race_bonus(race_id);
"""


def table_exists(
    db: sqlite3.Connection,
    table_name: str,
) -> bool:
    row = db.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def column_info(
    db: sqlite3.Connection,
    table_name: str,
) -> list[tuple]:
    return db.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()


def main():

    print()
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Racial Database Schema")
    print("=" * 60)
    print()

    print(f"Database: {DB_PATH}")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"ESO.db not found:\n{DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as db:

        db.execute(
            "PRAGMA foreign_keys = ON"
        )

        # Check whether the database is writable before
        # attempting the migration.
        db.execute(
            "BEGIN"
        )

        try:
            db.executescript(SCHEMA)
            db.commit()

        except Exception:
            db.rollback()
            raise

        print()
        print("Schema created/verified:")
        print()

        for table in (
            "race",
            "race_stat",
            "race_bonus",
        ):
            exists = table_exists(
                db,
                table,
            )

            print(
                f"  {'OK' if exists else 'MISSING':<8}"
                f"{table}"
            )

            if exists:
                for column in column_info(
                    db,
                    table,
                ):
                    # PRAGMA table_info:
                    # cid, name, type, notnull, default, pk
                    print(
                        f"      {column[1]:<18}"
                        f"{column[2]}"
                    )

        print()
        print(
            "Existing rows:"
        )

        for table in (
            "race",
            "race_stat",
            "race_bonus",
        ):
            count = db.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(
                f"  {table:<18}{count}"
            )

    print()
    print("=" * 60)
    print(" RACIAL SCHEMA READY")
    print("=" * 60)
    print()
    print(
        "No racial records were imported."
    )
    print(
        "The next step is the racial-data database importer."
    )


if __name__ == "__main__":
    main()