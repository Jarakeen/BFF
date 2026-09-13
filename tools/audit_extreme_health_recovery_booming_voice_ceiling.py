from __future__ import annotations

"""Inspect canonical evidence needed to bound Booming Voice Health Recovery.

This audit intentionally does not guess a recovery ceiling. It prints the canonical
Class Mastery tooltip, the shared Ultimate resource contract, and every matching
skill/ability/rank row for Booming Voice / The Storm Voice so the Extreme engine can
separate maximum stored Ultimate from the maximum amount actually spent by one
qualifying activation.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.class_mastery_repository import ClassMasteryRepository
from services.eso_character_progression_contract import ULTIMATE_RULES


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _select_existing(columns: set[str], names: tuple[str, ...], *, prefix: str = "") -> list[str]:
    result: list[str] = []
    for name in names:
        if name in columns:
            source = f"{prefix}.{name}" if prefix else name
            result.append(f"{source} AS {prefix + '_' if prefix else ''}{name}")
    return result


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    mastery = tuple(
        row
        for row in ClassMasteryRepository(database).all()
        if row.name.casefold() == "booming voice"
    )

    print("EXTREME HEALTH RECOVERY BOOMING VOICE CEILING EVIDENCE")
    print(f"database={database}")
    print("mode=canonical_evidence_not_assumed_numeric_ceiling")
    print()
    print("ULTIMATE CONTRACT")
    print(f"maximum_resource={ULTIMATE_RULES.maximum_resource}")
    print(f"one_ultimate_per_bar={ULTIMATE_RULES.one_ultimate_per_bar}")
    print(f"normal_cast_consumes_accumulated_resource={ULTIMATE_RULES.normal_cast_consumes_accumulated_resource}")
    print()

    print("CLASS MASTERY ROW")
    if not mastery:
        print("  <missing Booming Voice Class Mastery row>")
    for row in mastery:
        print(
            f"  class={row.class_name!r} skill_id={row.skill_id} base_ability_id={row.base_ability_id} "
            f"name={row.name!r}"
        )
        print(f"  description={row.description!r}")
    print()

    if not database.is_file():
        print("database_missing=True")
        return 2

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        skill_cols = _columns(db, "skill")
        rank_cols = _columns(db, "skill_rank")
        ability_cols = _columns(db, "ability")

        print("MATCHING SKILL ROWS")
        skill_select = _select_existing(
            skill_cols,
            (
                "id", "base_ability_id", "name", "class_type", "skill_line", "skill_type",
                "description", "is_passive", "is_player", "is_crafted",
            ),
            prefix="s",
        )
        if skill_select:
            text_parts = [
                part for part in (
                    "LOWER(COALESCE(s.name, ''))",
                    "LOWER(COALESCE(s.description, ''))" if "description" in skill_cols else "''",
                )
            ]
            rows = db.execute(
                f"SELECT {', '.join(skill_select)} FROM skill s "
                f"WHERE {' OR '.join(f'{part} LIKE ?' for part in text_parts for _ in (0, 1))} "
                "ORDER BY LOWER(COALESCE(s.name, '')), s.id",
                tuple(value for _part in text_parts for value in ("%storm voice%", "%booming voice%")),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <skill schema unavailable>")
        print()

        print("MATCHING SKILL RANK / ABILITY ROWS")
        if {"skill_id", "ability_id"}.issubset(rank_cols) and "id" in skill_cols:
            select = []
            select.extend(_select_existing(skill_cols, ("id", "name", "class_type", "skill_line"), prefix="s"))
            select.extend(_select_existing(rank_cols, ("ability_id", "rank", "morph", "cost", "raw_name", "raw_description"), prefix="sr"))
            select.extend(_select_existing(ability_cols, ("name", "base_mechanic", "description"), prefix="a"))
            ability_join = "LEFT JOIN ability a ON a.ability_id = sr.ability_id" if "ability_id" in ability_cols else ""
            predicates = ["LOWER(COALESCE(s.name, '')) LIKE ?"]
            params: list[str] = ["%storm voice%"]
            if "raw_name" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_name, '')) LIKE ?")
                params.append("%storm voice%")
            if "raw_description" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_description, '')) LIKE ?")
                params.append("%storm voice%")
            if "name" in ability_cols:
                predicates.append("LOWER(COALESCE(a.name, '')) LIKE ?")
                params.append("%storm voice%")
            if "description" in ability_cols:
                predicates.append("LOWER(COALESCE(a.description, '')) LIKE ?")
                params.append("%storm voice%")
            rows = db.execute(
                f"SELECT {', '.join(select)} FROM skill_rank sr "
                "JOIN skill s ON s.id = sr.skill_id "
                f"{ability_join} "
                f"WHERE {' OR '.join(predicates)} "
                "ORDER BY s.id, COALESCE(sr.rank, 0), COALESCE(sr.morph, 0), sr.ability_id",
                tuple(params),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <rank schema unavailable>")

    print()
    print("NEXT_STEP=determine whether Booming Voice scales from stored Ultimate, actual cast cost, or another explicit spend value; only then assign its numeric ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
