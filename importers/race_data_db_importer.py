"""
Black Feather Foundry
Racial Data -> ESO.db Importer

Reads:
    data/raw/racial_data.json

Writes:
    data/eso.db

Populates:
    race
    race_stat
    race_bonus

The import is idempotent:
    - existing races are updated
    - existing stats are updated
    - existing bonuses are preserved without duplication
    - stale stats/bonuses belonging to a race are removed before
      that race is re-imported

Everything is performed in one SQLite transaction.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "racial_data.json"
)

DB_PATH = (
    ROOT
    / "data"
    / "eso.db"
)


STAT_KEYS = {
    "max_magicka",
    "magicka_recovery",
    "spell_damage",
    "max_health",
    "health_recovery",
    "max_stamina",
    "stamina_recovery",
    "weapon_damage",
}


def load_source() -> list[dict]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"Racial data not found:\n{SOURCE_PATH}"
        )

    data = json.loads(
        SOURCE_PATH.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(data, dict):
        records = data.get("races")

    elif isinstance(data, list):
        records = data

    else:
        raise ValueError(
            "racial_data.json must contain "
            "a list or an object with a 'races' list."
        )

    if not isinstance(records, list):
        raise ValueError(
            "racial_data.json does not contain "
            "a valid 'races' list."
        )

    return records


def validate_records(
    records: list[dict],
) -> None:

    if not records:
        raise ValueError(
            "racial_data.json contains no races."
        )

    seen = set()

    for index, record in enumerate(
        records,
        1,
    ):

        if not isinstance(record, dict):
            raise ValueError(
                f"Race record {index} is not an object."
            )

        name = record.get("race")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Race record {index} has no valid race name."
            )

        key = name.strip().lower()

        if key in seen:
            raise ValueError(
                f"Duplicate race in source: {name}"
            )

        seen.add(key)

        stats = record.get(
            "bonuses",
            {},
        )

        if not isinstance(stats, dict):
            raise ValueError(
                f"{name}: bonuses must be an object."
            )

        for stat, value in stats.items():

            if stat not in STAT_KEYS:
                raise ValueError(
                    f"{name}: unknown stat key "
                    f"{stat!r}."
                )

            if not isinstance(value, int):
                raise ValueError(
                    f"{name}: stat {stat!r} "
                    f"must be an integer."
                )

        other_bonuses = record.get(
            "other_bonuses",
            [],
        )

        if not isinstance(
            other_bonuses,
            list,
        ):
            raise ValueError(
                f"{name}: other_bonuses must be a list."
            )


def get_race_id(
    db: sqlite3.Connection,
    name: str,
) -> int | None:

    row = db.execute(
        """
        SELECT id
        FROM race
        WHERE name = ?
        """,
        (name,),
    ).fetchone()

    return row[0] if row else None


def upsert_race(
    db: sqlite3.Connection,
    record: dict,
) -> int:

    name = record["race"].strip()
    alliance = (
        record.get("alliance")
        or None
    )
    association = (
        record.get("association")
        or None
    )

    db.execute(
        """
        INSERT INTO race (
            name,
            alliance,
            association
        )
        VALUES (?, ?, ?)
        ON CONFLICT(name)
        DO UPDATE SET
            alliance = excluded.alliance,
            association = excluded.association
        """,
        (
            name,
            alliance,
            association,
        ),
    )

    race_id = get_race_id(
        db,
        name,
    )

    if race_id is None:
        raise RuntimeError(
            f"Could not retrieve race id for {name!r}."
        )

    return race_id


def replace_stats(
    db: sqlite3.Connection,
    race_id: int,
    stats: dict,
) -> int:

    db.execute(
        """
        DELETE FROM race_stat
        WHERE race_id = ?
        """,
        (race_id,),
    )

    count = 0

    for stat, value in stats.items():

        db.execute(
            """
            INSERT INTO race_stat (
                race_id,
                stat,
                value
            )
            VALUES (?, ?, ?)
            """,
            (
                race_id,
                stat,
                value,
            ),
        )

        count += 1

    return count


def replace_bonuses(
    db: sqlite3.Connection,
    race_id: int,
    bonuses: list,
    source: str | None,
) -> int:

    db.execute(
        """
        DELETE FROM race_bonus
        WHERE race_id = ?
        """,
        (race_id,),
    )

    count = 0
    seen = set()

    for bonus in bonuses:

        if not isinstance(
            bonus,
            str,
        ):
            continue

        text = bonus.strip()

        if not text:
            continue

        key = text.lower()

        if key in seen:
            continue

        seen.add(key)

        db.execute(
            """
            INSERT INTO race_bonus (
                race_id,
                bonus_text,
                source
            )
            VALUES (?, ?, ?)
            """,
            (
                race_id,
                text,
                source,
            ),
        )

        count += 1

    return count


def import_records(
    records: list[dict],
) -> tuple[int, int, int]:

    races_imported = 0
    stats_imported = 0
    bonuses_imported = 0

    with sqlite3.connect(DB_PATH) as db:

        db.execute(
            "PRAGMA foreign_keys = ON"
        )

        try:
            db.execute("BEGIN")

            for record in records:

                race_id = upsert_race(
                    db,
                    record,
                )

                stat_count = replace_stats(
                    db,
                    race_id,
                    record.get(
                        "bonuses",
                        {},
                    ),
                )

                bonus_count = replace_bonuses(
                    db,
                    race_id,
                    record.get(
                        "other_bonuses",
                        [],
                    ),
                    record.get(
                        "source"
                    ),
                )

                races_imported += 1
                stats_imported += stat_count
                bonuses_imported += bonus_count

            db.commit()

        except Exception:
            db.rollback()
            raise

    return (
        races_imported,
        stats_imported,
        bonuses_imported,
    )


def verify_database() -> dict:

    with sqlite3.connect(DB_PATH) as db:

        race_count = db.execute(
            "SELECT COUNT(*) FROM race"
        ).fetchone()[0]

        stat_count = db.execute(
            "SELECT COUNT(*) FROM race_stat"
        ).fetchone()[0]

        bonus_count = db.execute(
            "SELECT COUNT(*) FROM race_bonus"
        ).fetchone()[0]

        argonian = db.execute(
            """
            SELECT
                r.name,
                r.alliance,
                r.association
            FROM race AS r
            WHERE r.name = 'Argonian'
            """
        ).fetchone()

        argonian_stats = db.execute(
            """
            SELECT stat, value
            FROM race_stat
            WHERE race_id = (
                SELECT id
                FROM race
                WHERE name = 'Argonian'
            )
            ORDER BY stat
            """
        ).fetchall()

        argonian_bonuses = db.execute(
            """
            SELECT bonus_text
            FROM race_bonus
            WHERE race_id = (
                SELECT id
                FROM race
                WHERE name = 'Argonian'
            )
            ORDER BY id
            """
        ).fetchall()

    return {
        "race_count": race_count,
        "stat_count": stat_count,
        "bonus_count": bonus_count,
        "argonian": argonian,
        "argonian_stats": argonian_stats,
        "argonian_bonuses": [
            row[0]
            for row in argonian_bonuses
        ],
    }


def main():

    print()
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Racial Data -> ESO.db Importer")
    print("=" * 60)
    print()

    print(
        f"Source: {SOURCE_PATH}"
    )

    print(
        f"Database: {DB_PATH}"
    )

    if not DB_PATH.exists():
        print()
        print(
            "ERROR: ESO.db does not exist."
        )
        sys.exit(1)

    try:
        records = load_source()

        validate_records(
            records
        )

        print()
        print(
            f"Source races: {len(records)}"
        )

        imported = import_records(
            records
        )

        print()
        print(
            "IMPORT SUMMARY"
        )
        print(
            f"  Races:        {imported[0]}"
        )
        print(
            f"  Stats:        {imported[1]}"
        )
        print(
            f"  Bonuses:      {imported[2]}"
        )

        verification = verify_database()

        print()
        print(
            "DATABASE TOTALS"
        )
        print(
            f"  race:         "
            f"{verification['race_count']}"
        )
        print(
            f"  race_stat:    "
            f"{verification['stat_count']}"
        )
        print(
            f"  race_bonus:   "
            f"{verification['bonus_count']}"
        )

        if verification["argonian"]:
            print()
            print(
                "ARGONIAN SPOT CHECK"
            )

            name, alliance, association = (
                verification["argonian"]
            )

            print(
                f"  {name}"
            )
            print(
                f"  Alliance:     {alliance}"
            )
            print(
                f"  Association:  {association}"
            )

            print(
                "  Stats:"
            )

            for stat, value in (
                verification["argonian_stats"]
            ):
                print(
                    f"    {stat}: {value}"
                )

            print(
                "  Bonuses:"
            )

            for bonus in (
                verification["argonian_bonuses"]
            ):
                print(
                    f"    - {bonus}"
                )

        print()
        print("=" * 60)
        print(" RACIAL DATABASE IMPORT PASSED")
        print("=" * 60)

    except Exception as exc:
        print()
        print(
            f"ERROR: {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()