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
        description="Bootstrap one canonical encounter row from legacy DB or raw UESP boss records"
    )
    ap.add_argument(
        "boss_selector",
        help="Exact legacy boss id/name or normalized canonical/raw UESP boss selector",
    )
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument(
        "--content-id",
        help=(
            "Explicit content id for raw UESP fallback. Required when the boss is "
            "not present in the legacy bosses table; never inferred automatically."
        ),
    )
    ap.add_argument(
        "--raw-bosses-dir",
        type=Path,
        default=Path("data/uesp/bosses"),
        help="Directory containing recovered raw UESP boss JSON records.",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually create/extend encounter schema and insert the encounter row.",
    )
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        plan = build_encounter_bootstrap_plan(
            connection,
            args.boss_selector,
            raw_bosses_dir=args.raw_bosses_dir,
            content_id=args.content_id,
        )

        print("=" * 76)
        print(" ENCOUNTER BOOTSTRAP")
        print("=" * 76)
        print(f"mode:             {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"database:         {args.database}")
        print(f"selector:         {args.boss_selector}")
        print(f"bootstrap source: {plan.bootstrap_source}")
        print(f"source record:    {plan.source_record}")
        print(f"legacy boss id:   {plan.legacy_boss_id or '(not present)'}")
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
