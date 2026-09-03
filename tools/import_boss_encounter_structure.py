from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.boss_encounter_structural_db_audit import (
    audit_boss_structural_database,
)
from services.boss_encounter_structural_import import (
    apply_boss_structural_import,
    audit_boss_structural_import,
)


def _default_backup_path(database: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return database.with_name(f"{database.name}.before-boss-structural-import.{stamp}")


def _backup_database(connection: sqlite3.Connection, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = sqlite3.connect(path)
    try:
        connection.backup(backup)
    finally:
        backup.close()


def _print_post_write_audit(audit) -> None:
    print("\nPOST-WRITE STRUCTURAL DB AUDIT")
    print(f"Boss source files:     {audit.bosses}")
    print(f"Health rows:           {audit.matched_health} / {audit.expected_health}")
    print(f"Ability rows:          {audit.matched_abilities} / {audit.expected_abilities}")
    print(f"Explicit phase rows:   {audit.matched_phases} / {audit.expected_phases}")
    print(f"Dialogue rows:         {audit.matched_dialogue} / {audit.expected_dialogue}")
    print(f"Section rows:          {audit.matched_sections} / {audit.expected_sections}")
    print(f"Problems:              {len(audit.problems)}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Import source-backed boss encounter structure without inferred mechanics"
    )
    ap.add_argument("--database", type=Path, default=Path("data/eso.db"))
    ap.add_argument("--source-dir", type=Path, default=Path("data/eso_info/bosses"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument(
        "--backup",
        type=Path,
        help=(
            "Backup path used before --apply. If omitted, a timestamped sibling of "
            "the database is created automatically."
        ),
    )
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
            print("\nRESULT: PASS")
            print("Dry run only. No structural encounter rows were changed.")
            print("Inferred mechanics and canonical facts are not part of this import.")
            return 0

        backup_path = args.backup or _default_backup_path(args.database)
        if backup_path.resolve() == args.database.resolve():
            print("\nRESULT: BLOCKED")
            print("Backup path must differ from the live database path.")
            return 1
        if backup_path.exists():
            print("\nRESULT: BLOCKED")
            print(f"Backup already exists and will not be overwritten: {backup_path}")
            return 1

        _backup_database(connection, backup_path)
        print(f"\nBackup created:       {backup_path}")

        bosses, abilities, phases, dialogue = apply_boss_structural_import(connection, audit)
        print("\nWRITE RESULT: COMMITTED")
        print(f"Bosses updated:       {bosses}")
        print(f"Abilities written:    {abilities}")
        print(f"Phases written:       {phases}")
        print(f"Dialogue written:     {dialogue}")
        print("No encounter_mechanic, encounter_strategy, or canonical fact rows were changed.")

        post_write = audit_boss_structural_database(connection, args.source_dir)
        _print_post_write_audit(post_write)
        if post_write.blocked:
            print("\nRESULT: BLOCKED")
            print("The write committed, but post-write verification found mismatches.")
            print(f"Restore source if needed from backup: {backup_path}")
            for problem in post_write.problems[:20]:
                print(f"  - {problem}")
            if len(post_write.problems) > 20:
                print(f"  ... {len(post_write.problems) - 20} more")
            return 2

        print("\nRESULT: PASS")
        print("Structural rows were written and independently verified against the source corpus.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
