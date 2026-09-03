from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.boss_parent_content_bootstrap import (
    AMBIGUOUS_SOURCE,
    INVALID_SOURCE,
    MISSING_SOURCE,
    audit_boss_parent_content,
)
from services.eso_db.eso_db_importer import EsoDbImporter


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Bootstrap only missing parent content required by tracked boss records"
    )
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument("--boss-dir", type=Path, default=Path("data/eso_info/bosses"))
    ap.add_argument("--content-root", type=Path, default=Path("data/eso_info"))
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Import the exact missing content records after a blocker-free preflight.",
    )
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    try:
        audit = audit_boss_parent_content(
            connection,
            boss_dir=args.boss_dir,
            content_root=args.content_root,
        )
    finally:
        connection.close()

    print("=" * 72)
    print(" BOSS PARENT CONTENT BOOTSTRAP")
    print("=" * 72)
    print(f"Mode:                 {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Database:             {args.database}")
    print(f"Boss source directory:{' ' * 5}{args.boss_dir}")
    print(f"Content source root:  {args.content_root}")
    print(f"Referenced contents:  {len(audit.candidates)}")
    print(f"Already canonical:    {len(audit.existing)}")
    print(f"Ready to import:      {len(audit.ready)}")
    print(f"Blocked:              {len(audit.blocked)}")

    if audit.ready:
        print("\nREADY")
        for row in audit.ready:
            print(
                f"  - {row.content_id} [{row.content_type}] bosses={row.boss_count} "
                f"source={row.source_path}"
            )

    if audit.blocked:
        print("\nBLOCKERS")
        for row in audit.blocked:
            print(f"  - [{row.status}] {row.content_id}: {row.reason}")
        print("\nNo content rows were changed.")
        return 2

    if not args.apply:
        print("\nDry run only. eso.db was not modified.")
        return 0

    imported = 0
    with EsoDbImporter(args.database) as importer:
        for row in audit.ready:
            if row.source_path is None:
                raise RuntimeError(f"Ready content candidate has no source path: {row.content_id}")
            importer.import_content_file(row.source_path)
            imported += 1

    print(f"\nImported missing content rows: {imported}")
    print("Existing content rows were not re-imported by this bootstrap pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
