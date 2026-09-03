from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_encounter_structural_db_audit import audit_boss_structural_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify persisted boss structural rows against the canonical source corpus.")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data" / "eso_info" / "bosses")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "eso.db")
    args = parser.parse_args()

    print("=" * 72)
    print(" PERSISTED BOSS STRUCTURAL ROW AUDIT")
    print("=" * 72)
    print(f"Database:                       {args.database}")
    print(f"Source directory:               {args.source_dir}")

    if not args.database.exists():
        print("\nRESULT: BLOCKED")
        print("Database file does not exist.")
        return 1

    con = sqlite3.connect(args.database)
    try:
        audit = audit_boss_structural_database(con, args.source_dir)
    finally:
        con.close()

    print(f"Boss source files:              {audit.bosses}")
    print(f"Health rows:                    {audit.matched_health} / {audit.expected_health}")
    print(f"Ability rows:                   {audit.matched_abilities} / {audit.expected_abilities}")
    print(f"Explicit phase rows:            {audit.matched_phases} / {audit.expected_phases}")
    print(f"Dialogue rows:                  {audit.matched_dialogue} / {audit.expected_dialogue}")
    print(f"Section rows:                   {audit.matched_sections} / {audit.expected_sections}")
    print(f"Missing/conflicting/extra rows: {len(audit.problems)}")

    if audit.blocked:
        print("\nRESULT: BLOCKED")
        for problem in audit.problems[:20]:
            print(f"  - {problem}")
        return 1

    print("\nRESULT: PASS")
    print("Persisted boss health, abilities, phases, dialogue, sections, and provenance exactly match the source corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
