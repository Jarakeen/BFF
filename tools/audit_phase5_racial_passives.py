from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect canonical skill/rank evidence for racial passives before "
            "Phase 5 racial stat resolution is implemented."
        )
    )
    parser.add_argument("--race", default="Breton", help="Race to inspect.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


def _columns(db: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in db.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _existing(columns: list[str], candidates: tuple[str, ...]) -> list[str]:
    available = set(columns)
    return [name for name in candidates if name in available]


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    if not database.exists():
        print(f"Database not found: {database}")
        return 2

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        skill_columns = _columns(db, "skill")
        rank_columns = _columns(db, "skill_rank")
        ability_columns = _columns(db, "ability")

        print("=" * 78)
        print(" PHASE 5 RACIAL PASSIVE CANONICAL-DATA DIAGNOSTIC")
        print("=" * 78)
        print(f"Race:     {args.race}")
        print(f"Database: {database}")
        print()
        print("skill columns:")
        print("  " + ", ".join(skill_columns))
        print("skill_rank columns:")
        print("  " + ", ".join(rank_columns))
        print("ability columns:")
        print("  " + ", ".join(ability_columns))
        print()

        skill_select = _existing(
            skill_columns,
            (
                "id",
                "name",
                "skill_line",
                "class_type",
                "description",
                "base_ability_id",
                "is_passive",
                "is_player",
            ),
        )
        rank_select = _existing(
            rank_columns,
            (
                "skill_id",
                "ability_id",
                "display_id",
                "rank",
                "morph",
                "raw_name",
                "raw_coef",
                "coef_types",
            ),
        )
        ability_select = _existing(
            ability_columns,
            (
                "ability_id",
                "name",
                "description",
                "skill_line",
                "class_type",
                "rank",
                "morph",
                "base_ability_id",
                "base_mechanic",
                "cost",
                "buff_type",
            ),
        )

        if not {"id", "name", "is_passive"}.issubset(set(skill_columns)):
            print("Required skill columns are missing; cannot inspect racial passives.")
            return 3
        if not {"skill_id", "rank"}.issubset(set(rank_columns)):
            print("Required skill_rank columns are missing; cannot inspect racial ranks.")
            return 3

        rows = db.execute(
            """
            SELECT s.*
            FROM skill s
            WHERE COALESCE(s.is_passive, 0) = 1
              AND (
                    LOWER(TRIM(COALESCE(s.skill_line, ''))) IN (
                        'racial', 'racial skill', 'racial skills',
                        LOWER(TRIM(?)), LOWER(TRIM(?))
                    )
                    OR LOWER(TRIM(COALESCE(s.skill_line, ''))) LIKE LOWER(TRIM(?))
                  )
            ORDER BY s.name COLLATE NOCASE
            """,
            (
                args.race,
                f"{args.race} Skills",
                f"%{args.race}%",
            ),
        ).fetchall()

        print(f"Candidate passive skills: {len(rows)}")
        print()

        for skill in rows:
            skill_id = skill["id"]
            print("-" * 78)
            print(f"Skill: {skill['name']}")
            for column in skill_select:
                if column in {"id", "name"}:
                    continue
                print(f"  skill.{column}: {skill[column]}")

            rank_rows = db.execute(
                "SELECT * FROM skill_rank WHERE skill_id = ? ORDER BY rank, morph, ability_id",
                (skill_id,),
            ).fetchall()
            print(f"  ranks: {len(rank_rows)}")
            for rank_row in rank_rows:
                print(f"    rank {rank_row['rank']}")
                for column in rank_select:
                    if column in {"skill_id", "rank"}:
                        continue
                    print(f"      skill_rank.{column}: {rank_row[column]}")

                ability_id = rank_row["ability_id"] if "ability_id" in rank_columns else None
                if ability_id is None or "ability_id" not in ability_columns:
                    continue
                ability = db.execute(
                    "SELECT * FROM ability WHERE ability_id = ? LIMIT 1",
                    (ability_id,),
                ).fetchone()
                if ability is None:
                    continue
                for column in ability_select:
                    if column == "ability_id":
                        continue
                    print(f"      ability.{column}: {ability[column]}")

        print()
        print("=" * 78)
        print("Use this output to determine whether per-rank racial effects are canonical")
        print("in eso.db or whether the racial importer must be upgraded first.")
        print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
