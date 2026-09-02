from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_source_alignment_issue_repository import (
    SkillComponentSourceAlignmentIssueRepository,
)
from minmax.skill_component_source_stat_rule_repository import (
    SkillComponentSourceStatRuleRepository,
)
from tools.audit_phase6_closeout import load_phase6_closeout

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print only Phase 6 source-evidence rows that remain unexplained by canonical source-alignment handling."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    path = Path(args.database)
    rows = load_phase6_closeout(path)
    source_rows = [row for row in rows if row.closeout_status == "SOURCE_EVIDENCE_BLOCKED"]
    alignment_repo = SkillComponentSourceAlignmentIssueRepository(path)
    stat_repo = SkillComponentSourceStatRuleRepository(path)
    unresolved = [
        row
        for row in source_rows
        if not alignment_repo.resolve(row.skill_rank_id, row.coefficient_number)
        and not stat_repo.resolve(row.skill_rank_id, row.coefficient_number)
    ]

    print("\n========================================")
    print(" PHASE 6 UNRESOLVED SOURCE BLOCKS")
    print("========================================")
    print(f"Database:         {path}")
    print(f"Source rows:      {len(source_rows)}")
    print(f"Still unresolved: {len(unresolved)}")

    if not unresolved:
        return 0

    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        a_cols = _columns(db, "ability")
        sr_cols = _columns(db, "skill_rank")
        raw_json_expr = "a.raw_json" if "raw_json" in a_cols else "NULL"
        raw_desc_expr = "a.raw_description" if "raw_description" in a_cols else "NULL"
        coef_desc_expr = "a.coef_description" if "coef_description" in a_cols else "NULL"
        raw_tooltip_expr = "a.raw_tooltip" if "raw_tooltip" in a_cols else "NULL"
        raw_coef_expr = "sr.raw_coef" if "raw_coef" in sr_cols else "NULL"
        coef_types_expr = "sr.coef_types" if "coef_types" in sr_cols else "NULL"

        for item in unresolved:
            row = db.execute(
                f"""
                SELECT sr.id AS skill_rank_id, sr.ability_id, a.name,
                       {coef_desc_expr} AS coef_description,
                       {raw_desc_expr} AS raw_description,
                       {raw_tooltip_expr} AS raw_tooltip,
                       {raw_json_expr} AS raw_json,
                       {raw_coef_expr} AS raw_coef,
                       {coef_types_expr} AS coef_types
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (item.skill_rank_id,),
            ).fetchone()
            if row is None:
                continue

            desc_header = ""
            if row["raw_json"]:
                try:
                    payload = json.loads(str(row["raw_json"]))
                    if isinstance(payload, dict):
                        desc_header = str(payload.get("descHeader") or "")
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass

            print("\n----------------------------------------")
            print(
                f"rank={item.skill_rank_id} coef={item.coefficient_number} "
                f"ability={item.ability_id} name={item.ability_name}"
            )
            print(f"reason={item.reason}")
            print(f"fragment={item.fragment}")
            if desc_header:
                print(f"desc_header={_clean(desc_header)}")
            print(f"coef_description={_clean(row['coef_description'])}")
            print(f"raw_description={_clean(row['raw_description'])}")
            if row["raw_tooltip"]:
                print(f"raw_tooltip={_clean(row['raw_tooltip'])}")
            if row["raw_coef"]:
                print(f"raw_coef={_clean(row['raw_coef'])}")
            if row["coef_types"]:
                print(f"coef_types={_clean(row['coef_types'])}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
