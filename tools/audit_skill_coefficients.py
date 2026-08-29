from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone() is not None


def audit(database_path: str | Path = DEFAULT_DATABASE) -> int:
    path = Path(database_path)
    if not path.exists():
        print(f"Database not found: {path}")
        return 1

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        required = ("skill", "skill_rank", "skill_coefficient", "ability")
        missing = [name for name in required if not _table_exists(connection, name)]
        if missing:
            print("Missing required tables: " + ", ".join(missing))
            return 2

        skill_count = connection.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        rank_count = connection.execute("SELECT COUNT(*) FROM skill_rank").fetchone()[0]
        coefficient_count = connection.execute("SELECT COUNT(*) FROM skill_coefficient").fetchone()[0]
        covered_ranks = connection.execute(
            "SELECT COUNT(DISTINCT skill_rank_id) FROM skill_coefficient"
        ).fetchone()[0]
        type_rows = connection.execute(
            "SELECT type, COUNT(*) AS n FROM skill_coefficient GROUP BY type ORDER BY n DESC"
        ).fetchall()
        coefficient_types = Counter({str(row["type"]): int(row["n"]) for row in type_rows})

        samples = connection.execute(
            """
            WITH component_counts AS (
                SELECT skill_rank_id, COUNT(*) AS component_count
                FROM skill_coefficient
                WHERE type = '8' AND COALESCE(a, -1) >= 0
                GROUP BY skill_rank_id
            ), ranked AS (
                SELECT
                    sr.id AS skill_rank_id,
                    sr.ability_id,
                    sr.rank,
                    sr.morph,
                    s.base_ability_id,
                    COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '') AS name,
                    cc.component_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY sr.skill_id, sr.morph
                        ORDER BY COALESCE(sr.rank, 0) DESC, sr.ability_id DESC
                    ) AS rn
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                JOIN component_counts cc ON cc.skill_rank_id = sr.id
                WHERE COALESCE(s.is_player, 0) = 1
            )
            SELECT *
            FROM ranked
            WHERE rn = 1 AND component_count = 1
            ORDER BY name COLLATE NOCASE
            LIMIT 30
            """
        ).fetchall()

    print()
    print("========================================")
    print(" PHASE 3 SKILL COEFFICIENT AUDIT")
    print("========================================")
    print(f"Database:              {path}")
    print(f"Canonical skills:      {skill_count:,}")
    print(f"Skill ranks:           {rank_count:,}")
    print(f"Coefficient rows:      {coefficient_count:,}")
    print(f"Ranks with coefficients: {covered_ranks:,}")
    print()
    print("Coefficient types:")
    if coefficient_types:
        for coefficient_type, count in coefficient_types.most_common():
            print(f"  type {coefficient_type:>4}: {count:,}")
    else:
        print("  (none)")

    print()
    print("One-component type-8 player-skill candidates:")
    if not samples:
        print("  (none found)")
    else:
        for row in samples:
            print(
                f"  {row['name']} | ability={row['ability_id']} | "
                f"base={row['base_ability_id']} | rank={row['rank']} | morph={row['morph']}"
            )
    print()

    if coefficient_count == 0:
        print("Coefficient table exists but contains no rows. Re-run the canonical skills importer before Phase 3 validation.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(audit())
