from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE

DEFAULT_SKILLS = (
    "Combat Prayer",
    "Aggressive Horn",
    "Expansive Frost Cloak",
    "Overflowing Altar",
)


def _tables(db: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _columns(db: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in db.execute(f"PRAGMA table_info({table})"))


def _ability_rows(db: sqlite3.Connection, name: str):
    columns = _columns(db, "ability")
    wanted = [
        column
        for column in (
            "ability_id",
            "name",
            "skill_line",
            "class_type",
            "base_ability_id",
            "rank",
            "morph",
            "base_mechanic",
            "target",
            "duration",
            "description",
        )
        if column in columns
    ]
    rows = db.execute(
        f"SELECT {', '.join(wanted)} FROM ability "
        "WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) "
        "ORDER BY COALESCE(rank, 0), ability_id",
        (name,),
    ).fetchall()
    return wanted, rows


def _linked_effects(db: sqlite3.Connection, ability_id: int):
    tables = _tables(db)
    required = {"ability_effect_link", "effect_variant", "effect"}
    if not required.issubset(tables):
        return ()

    ael_columns = set(_columns(db, "ability_effect_link"))
    source_join = ""
    source_select = "NULL AS source_name, NULL AS source_condition"
    if "effect_source" in tables and "effect_source_id" in ael_columns:
        source_join = "LEFT JOIN effect_source es ON es.id = ael.effect_source_id"
        source_select = "es.source_name, es.condition"

    rows = db.execute(
        f"""
        SELECT
            ael.id,
            ael.effect_variant_id,
            e.id,
            e.name,
            e.category,
            ev.type,
            {source_select}
        FROM ability_effect_link ael
        JOIN effect_variant ev ON ev.id = ael.effect_variant_id
        JOIN effect e ON e.id = ev.effect_id
        {source_join}
        WHERE ael.ability_id = ?
        ORDER BY ael.id
        """,
        (ability_id,),
    ).fetchall()
    return tuple(rows)


def audit(database: Path, names: tuple[str, ...]) -> int:
    if not database.exists():
        print(f"Database not found: {database}")
        return 1

    with sqlite3.connect(database) as db:
        tables = _tables(db)
        if "ability" not in tables:
            print("Database has no ability table.")
            return 2

        print("========================================")
        print(" PHASE 5 SKILL EFFECT EVIDENCE AUDIT")
        print("========================================")
        print(f"Database: {database}")
        print("Read only: no database or saved-build data will be changed.")

        for name in names:
            print()
            print("----------------------------------------")
            print(name)
            print("----------------------------------------")

            columns, rows = _ability_rows(db, name)
            if not rows:
                print("ability rows: none")
                continue

            print(f"ability rows: {len(rows)}")
            for row in rows:
                values = dict(zip(columns, row))
                ability_id = int(values["ability_id"])
                summary = " | ".join(
                    f"{column}={values[column]!r}"
                    for column in columns
                    if column != "description"
                )
                print(f"  - {summary}")
                description = values.get("description")
                if description:
                    print(f"    description={description}")

                links = _linked_effects(db, ability_id)
                if not links:
                    print("    linked effects: none")
                else:
                    print(f"    linked effects: {len(links)}")
                    for (
                        link_id,
                        variant_id,
                        effect_id,
                        effect_name,
                        category,
                        variant_type,
                        source_name,
                        source_condition,
                    ) in links:
                        print(
                            "      - "
                            f"link_id={link_id} | variant_id={variant_id} | "
                            f"effect_id={effect_id} | effect={effect_name!r} | "
                            f"category={category!r} | variant_type={variant_type!r} | "
                            f"source={source_name!r} | condition={source_condition!r}"
                        )

    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect ability rows and imported effect links for selected Phase 5 skills."
        )
    )
    parser.add_argument("names", nargs="*", default=list(DEFAULT_SKILLS))
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(audit(args.database, tuple(args.names)))
