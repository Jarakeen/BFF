from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import load_decisions
from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics
from services.reviewed_single_source_mechanic_db_audit import (
    audit_reviewed_single_source_database,
)
from services.reviewed_single_source_mechanic_persistence import (
    build_reviewed_single_source_plans,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify persisted reviewed single-source boss mechanics against source and review manifest."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT / "data" / "eso_info" / "bosses",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "encounter_reviews" / "inferred_boss_mechanics.json",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "eso.db",
    )
    args = parser.parse_args()

    print("=" * 72)
    print(" PERSISTED REVIEWED SINGLE-SOURCE MECHANIC AUDIT")
    print("=" * 72)
    print(f"Database:                       {args.database}")

    if not args.database.exists():
        print("RESULT: BLOCKED")
        print("Database file does not exist.")
        return 1

    source_audit = audit_inferred_boss_mechanics(args.source_dir)
    if source_audit.failures:
        print("RESULT: BLOCKED")
        print(f"Source parse failures:          {len(source_audit.failures)}")
        return 1

    decisions = load_decisions(args.manifest)
    plans = build_reviewed_single_source_plans(source_audit.rows, decisions)

    con = sqlite3.connect(args.database)
    try:
        audit = audit_reviewed_single_source_database(con, plans)
    finally:
        con.close()

    print(f"Expected canonical facts:       {audit.expected_facts}")
    print(f"Matched canonical facts:        {audit.matched_facts}")
    print(f"Missing canonical facts:        {len(audit.missing_facts)}")
    print(f"Conflicting canonical facts:    {len(audit.conflicting_facts)}")
    print(f"Expected evidence rows:         {audit.expected_evidence}")
    print(f"Matched evidence rows:          {audit.matched_evidence}")
    print(f"Missing evidence rows:          {len(audit.missing_evidence)}")
    print(f"Conflicting evidence rows:      {len(audit.conflicting_evidence)}")

    if audit.blocked:
        print("\nRESULT: BLOCKED")
        for label in (
            list(audit.missing_facts)
            + list(audit.conflicting_facts)
            + list(audit.missing_evidence)
            + list(audit.conflicting_evidence)
        )[:10]:
            print(f"  - {label}")
        return 1

    print("\nRESULT: PASS")
    print("Persisted canonical facts and UESP evidence exactly match the accepted review plans.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
