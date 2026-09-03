from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.boss_encounter_bootstrap import (
    BLOCKING_STATUSES,
    apply_boss_encounter_bootstrap,
    audit_boss_encounter_bootstrap,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Plan or apply canonical encounter identities for the tracked ESO boss corpus"
    )
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument("--source-dir", type=Path, default=Path("data/eso_info/bosses"))
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Insert all non-blocked canonical encounter identities in one transaction.",
    )
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        audit = audit_boss_encounter_bootstrap(connection, args.source_dir)
        counts = Counter(row.status for row in audit.candidates)

        print("=" * 72)
        print(" BOSS ENCOUNTER CORPUS BOOTSTRAP")
        print("=" * 72)
        print(f"Mode:                 {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"Database:             {args.database}")
        print(f"Source directory:     {args.source_dir}")
        print(f"Boss source files:    {len(audit.candidates)}")
        print(f"Ready to insert:      {counts['ready']}")
        print(f"Already canonical:    {counts['existing']}")
        print(f"Missing content:      {counts['missing_content']}")
        print(f"Identity conflicts:   {counts['conflict']}")
        print(f"Duplicate boss IDs:   {counts['duplicate_id']}")
        print(f"Invalid source files: {counts['invalid_source']}")

        blockers = [row for row in audit.candidates if row.status in BLOCKING_STATUSES]
        if blockers:
            print("\nBLOCKERS")
            for row in blockers[:40]:
                label = row.encounter_id or row.source_path.name
                content = f" content={row.content_id}" if row.content_id else ""
                print(f"  - [{row.status}] {label}{content}: {row.reason}")
            if len(blockers) > 40:
                print(f"  ... {len(blockers) - 40} more")

        if not args.apply:
            print("\nDry run only. eso.db was not modified.")
            return 0 if not blockers else 2

        if blockers:
            print("\nRESULT: BLOCKED")
            print("No encounter rows were written because the batch contains blockers.")
            return 2

        inserted, existing = apply_boss_encounter_bootstrap(connection, audit)
        print("\nRESULT: COMMITTED")
        print(f"Inserted encounter rows: {inserted}")
        print(f"Existing encounter rows: {existing}")
        print("Only canonical encounter identities were changed; mechanics remain review evidence.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
