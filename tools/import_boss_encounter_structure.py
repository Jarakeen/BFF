from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.boss_encounter_structural_import import (
    apply_boss_structural_import,
    audit_boss_structural_import,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Import source-backed boss encounter structure without inferred mechanics"
    )
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument("--source-dir", type=Path, default=Path("data/eso_info/bosses"))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        audit = audit_boss_structural_import(connection, args.source_dir)
        print("=" * 72)
        print(" BOSS ENCOUNTER STRUCTURAL IMPORT")
        print("=" * 72)
        print(f"Mode:                 {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"Database:             {args.database}")
        print(f"Source directory:     {args.source_dir}")
        print(f"Boss source files:    {len(audit.candidates)}")
        print(f"Ready bosses:         {len(audit.ready)}")
        print(f"Abilities:            {audit.ability_count}")
        print(f"Explicit phases:      {audit.phase_count}")
        print(f"Dialogue rows:        {audit.dialogue_count}")
        print(f"Blocked:              {len(audit.blocked)}")

        if audit.blocked:
            print("\nBLOCKERS")
            for row in audit.blocked[:40]:
                print(f"  - [{row.status}] {row.encounter_id or row.source_path.name}: {row.reason}")
            if len(audit.blocked) > 40:
                print(f"  ... {len(audit.blocked) - 40} more")
            print("\nRESULT: BLOCKED")
            print("No rows were changed.")
            return 1

        if not args.apply:
            print("\nDry run only. No structural encounter rows were changed.")
            print("Inferred mechanics and canonical facts are not part of this import.")
            return 0

        bosses, abilities, phases, dialogue = apply_boss_structural_import(connection, audit)
        print("\nRESULT: COMMITTED")
        print(f"Bosses updated:       {bosses}")
        print(f"Abilities written:    {abilities}")
        print(f"Phases written:       {phases}")
        print(f"Dialogue written:     {dialogue}")
        print("No encounter_mechanic, encounter_strategy, or canonical fact rows were changed.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
