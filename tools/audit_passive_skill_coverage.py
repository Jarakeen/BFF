from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit passive-skill data available for the shared Phase 2 stat pipeline. "
            "This tool does not apply passive effects; it inventories canonical DB data "
            "so passives can be modeled without hardcoded per-build guesses."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--class", dest="class_name", default="", help="Optional class_type filter")
    parser.add_argument("--show-descriptions", action="store_true")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row

    skill_columns = _columns(connection, "skill")
    rank_columns = _columns(connection, "skill_rank")
    ability_columns = _columns(connection, "ability")

    required_skill = {"id", "name", "class_type", "skill_line", "is_passive"}
    missing = sorted(required_skill - skill_columns)
    if missing:
        print(f"skill table is missing required passive-audit columns: {', '.join(missing)}")
        return 2

    description_expr = "s.description AS description" if "description" in skill_columns else "'' AS description"
    base_id_expr = "s.base_ability_id AS base_ability_id" if "base_ability_id" in skill_columns else "NULL AS base_ability_id"

    rank_join = ""
    rank_select = "NULL AS max_rank, NULL AS max_rank_ability_id"
    if {"skill_id", "rank", "ability_id"}.issubset(rank_columns):
        rank_join = """
            LEFT JOIN (
                SELECT sr.skill_id, MAX(sr.rank) AS max_rank
                FROM skill_rank sr
                GROUP BY sr.skill_id
            ) ranks ON ranks.skill_id = s.id
            LEFT JOIN skill_rank max_sr
                ON max_sr.skill_id = s.id
               AND max_sr.rank = ranks.max_rank
        """
        rank_select = "ranks.max_rank AS max_rank, MAX(max_sr.ability_id) AS max_rank_ability_id"

    concrete_description_expr = "'' AS concrete_description"
    ability_join = ""
    if "ability_id" in ability_columns and "description" in ability_columns and rank_join:
        ability_join = "LEFT JOIN ability a ON a.ability_id = max_sr.ability_id"
        concrete_description_expr = "MAX(COALESCE(NULLIF(a.description, ''), '')) AS concrete_description"

    where = "WHERE COALESCE(s.is_passive, 0) != 0"
    params: list[str] = []
    if args.class_name.strip():
        where += " AND LOWER(TRIM(COALESCE(s.class_type, ''))) = LOWER(TRIM(?))"
        params.append(args.class_name.strip())

    query = f"""
        SELECT
            s.id,
            s.name,
            COALESCE(s.class_type, '') AS class_type,
            COALESCE(s.skill_line, '') AS skill_line,
            {base_id_expr},
            {description_expr},
            {rank_select},
            {concrete_description_expr}
        FROM skill s
        {rank_join}
        {ability_join}
        {where}
        GROUP BY s.id, s.name, s.class_type, s.skill_line, s.base_ability_id, s.description, ranks.max_rank
        ORDER BY
            COALESCE(s.class_type, '') COLLATE NOCASE,
            COALESCE(s.skill_line, '') COLLATE NOCASE,
            s.name COLLATE NOCASE
    """

    try:
        rows = connection.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        # Fallback for older/local schemas lacking columns used only in GROUP BY.
        query = f"""
            SELECT
                s.id,
                s.name,
                COALESCE(s.class_type, '') AS class_type,
                COALESCE(s.skill_line, '') AS skill_line,
                {base_id_expr},
                {description_expr},
                NULL AS max_rank,
                NULL AS max_rank_ability_id,
                '' AS concrete_description
            FROM skill s
            {where}
            ORDER BY
                COALESCE(s.class_type, '') COLLATE NOCASE,
                COALESCE(s.skill_line, '') COLLATE NOCASE,
                s.name COLLATE NOCASE
        """
        rows = connection.execute(query, params).fetchall()

    print("========================================")
    print(" PASSIVE SKILL DATA COVERAGE AUDIT")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Filter:   {args.class_name or '(all classes/skill lines)'}")
    print(f"Passives: {len(rows)}")

    current_group: tuple[str, str] | None = None
    for row in rows:
        group = (str(row["class_type"] or "") or "(non-class)", str(row["skill_line"] or "") or "(unknown line)")
        if group != current_group:
            current_group = group
            print(f"\n[{group[0]} | {group[1]}]")

        rank = row["max_rank"]
        ability_id = row["max_rank_ability_id"]
        suffix = []
        if rank is not None:
            suffix.append(f"rank {rank}")
        if ability_id is not None:
            suffix.append(f"ability {ability_id}")
        detail = f" ({', '.join(suffix)})" if suffix else ""
        print(f"  - {row['name']}{detail}")

        if args.show_descriptions:
            description = str(row["concrete_description"] or row["description"] or "").strip()
            if description:
                print(f"      {description}")
            else:
                print("      [no description available]")

    print("\nNOTE: inventory only. No passive is applied to combat math by this tool.")
    print("A passive should enter the shared stat pipeline only after its effect and activation rule are verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
