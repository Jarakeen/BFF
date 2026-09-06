from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.eso_markup import normalize_eso_markup
from minmax.skill_coefficient_repository import SkillCoefficientRepository


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})"))


def _display_value(value) -> str:
    if isinstance(value, str):
        # Database descriptions preserve ESO tooltip color markup such as
        # |cffffff75|r. Audits are plain text, so keep the value and discard
        # the rendering tokens. Collapse source line breaks for readable rows.
        return " ".join(normalize_eso_markup(value).text.split())
    return str(value)


def _print_rows(title: str, rows: list[sqlite3.Row]) -> None:
    print(title)
    print("-" * len(title))
    if not rows:
        print("none")
        print()
        return
    for row in rows:
        values = []
        for key in row.keys():
            value = row[key]
            if value is None or value == "":
                continue
            values.append(f"{key}={_display_value(value)}")
        print(" | ".join(values) or "(empty row)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect canonical DB evidence for a saved Ultimate cost without inferring values"
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--ability-id", type=int)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    args = parser.parse_args()

    database = Path(args.database)
    repository = SkillCoefficientRepository(database)
    resolution = (
        repository.resolve_ability_id(args.ability_id)
        if args.ability_id is not None
        else repository.resolve_name(args.name)
    )
    rank = resolution.rank

    print("=" * 62)
    print(" PHASE 13 ULTIMATE COST EVIDENCE AUDIT")
    print("=" * 62)
    print(f"Requested name:       {args.name}")
    print(f"Requested ability ID: {args.ability_id if args.ability_id is not None else 'name resolution'}")
    print(f"Database:             {database}")
    print("Boundary:             diagnostic only; no Ultimate cost is inferred")
    print()

    if rank is None:
        print("RESOLUTION")
        print("----------")
        for item in resolution.unresolved or ("unresolved",):
            print(item)
        return 2

    print("RESOLVED SKILL RANK")
    print("-------------------")
    print(f"entity_id:       {rank.entity_id}")
    print(f"skill_rank_id:   {rank.skill_rank_id}")
    print(f"skill_id:        {rank.skill_id}")
    print(f"ability_id:      {rank.ability_id}")
    print(f"base_ability_id: {rank.base_ability_id}")
    print(f"name:            {rank.name}")
    print(f"rank / morph:    {rank.rank} / {rank.morph}")
    if resolution.unresolved:
        print("resolution notes: " + " | ".join(resolution.unresolved))
    print()

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]

        if "ability" in tables:
            ability_columns = _columns(connection, "ability")
            selected = [
                column
                for column in (
                    "ability_id",
                    "name",
                    "rank",
                    "morph",
                    "base_cost",
                    "base_mechanic",
                    "skill_line",
                    "description",
                    "duration",
                    "cost",
                    "mechanic",
                    "parent_ability_id",
                    "source_ability_id",
                )
                if column in ability_columns
            ]
            select_sql = ", ".join(selected) if selected else "*"
            exact_rows = connection.execute(
                f"SELECT {select_sql} FROM ability WHERE ability_id IN (?, ?) ORDER BY ability_id",
                (rank.ability_id, rank.base_ability_id),
            ).fetchall()
            _print_rows("ABILITY ROWS: RESOLVED + BASE ID", list(exact_rows))

            name_rows = connection.execute(
                f"SELECT {select_sql} FROM ability "
                "WHERE LOWER(name) LIKE LOWER(?) OR LOWER(name) LIKE LOWER(?) "
                "ORDER BY ability_id",
                (f"%{args.name}%", "%Guardian%"),
            ).fetchall()
            _print_rows("ABILITY ROWS: NAME / GUARDIAN MATCHES", list(name_rows))

        if "skill_rank" in tables:
            skill_rank_columns = _columns(connection, "skill_rank")
            selected = [
                column
                for column in (
                    "id",
                    "skill_id",
                    "ability_id",
                    "rank",
                    "morph",
                    "raw_name",
                    "duration",
                    "cost",
                    "base_cost",
                    "base_mechanic",
                )
                if column in skill_rank_columns
            ]
            select_sql = ", ".join(selected) if selected else "*"
            rows = connection.execute(
                f"SELECT {select_sql} FROM skill_rank WHERE skill_id = ? ORDER BY rank, morph, ability_id",
                (rank.skill_id,),
            ).fetchall()
            _print_rows("SKILL_RANK ROWS FOR LOGICAL SKILL", list(rows))

        print("TABLES WITH COST / MECHANIC / ABILITY-LINK COLUMNS")
        print("--------------------------------------------------")
        found = False
        interesting_tokens = (
            "cost",
            "mechanic",
            "ability_id",
            "parent",
            "source_ability",
            "linked",
            "trigger",
        )
        for table in tables:
            columns = _columns(connection, table)
            interesting = [
                column
                for column in columns
                if any(token in column.casefold() for token in interesting_tokens)
            ]
            if not interesting:
                continue
            found = True
            print(f"{table}: {', '.join(interesting)}")
        if not found:
            print("none")

    print()
    print("Interpretation: use this output to locate canonical spend evidence. ")
    print("Do not promote a cost into AbilityCostRepository unless the DB/source linkage is explicit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
