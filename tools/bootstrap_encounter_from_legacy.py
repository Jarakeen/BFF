from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_bootstrap import (
    apply_encounter_bootstrap,
    build_encounter_bootstrap_plan,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Bootstrap one canonical encounter row from legacy bosses/content records"
    )
    ap.add_argument("boss_id", help="Legacy bosses.id / canonical encounter id")
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually create/extend encounter schema and insert the encounter row.",
    )
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        plan = build_encounter_bootstrap_plan(connection, args.boss_id)

        print("=" * 76)
        print(" ENCOUNTER BOOTSTRAP FROM LEGACY RECORDS")
        print("=" * 76)
        print(f"mode:             {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"database:         {args.database}")
        print(f"encounter_id:     {plan.encounter_id}")
        print(f"content_id:       {plan.content_id}")
        print(f"name:             {plan.name}")
        print(f"slug:             {plan.slug}")
        print(f"source title:     {plan.source_page_title or '(none)'}")
        print(f"source revision:  {plan.source_revision_id or '(unresolved)'}")

        if not args.apply:
            print("\nDry run only. No schema objects or SQLite rows were changed.")
            return 0

        try:
            connection.execute("BEGIN")
            status = apply_encounter_bootstrap(connection, plan)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        print(f"\nresult:           {status}")
        print("Encounter bootstrap transaction committed.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
