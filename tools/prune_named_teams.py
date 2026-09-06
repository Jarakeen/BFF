from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import sys

from engine.config import DEFAULT_DATABASE


DEFAULT_KEEP = ("Swine & Punishment", "Disappointing Feral")


def _normalized(values: list[str] | tuple[str, ...]) -> set[str]:
    return {str(value or "").strip().casefold() for value in values if str(value or "").strip()}


def _existing_names(connection: sqlite3.Connection, table: str) -> list[str]:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    if row is None:
        return []
    return [str(item[0]) for item in connection.execute(f"SELECT name FROM {table}").fetchall()]


def _backup_database(database: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = database.with_name(f"{database.name}.before-team-prune.{stamp}")
    shutil.copy2(database, backup)
    return backup


def prune(database: Path, keep_names: tuple[str, ...], *, apply: bool) -> int:
    if not database.exists():
        print(f"Database not found: {database}")
        return 2

    keep = _normalized(keep_names)
    if not keep:
        print("Refusing to prune every team: at least one --keep name is required.")
        return 2

    connection = sqlite3.connect(database)
    try:
        roster_names = _existing_names(connection, "team")
        plan_names = _existing_names(connection, "generated_roster_plan")
        all_names = sorted(set(roster_names) | set(plan_names), key=str.casefold)
        remove_names = [name for name in all_names if name.casefold() not in keep]
        surviving = [name for name in all_names if name.casefold() in keep]

        print("========================================")
        print(" BFF NAMED TEAM PRUNE")
        print("========================================")
        print(f"Database: {database}")
        print("Keep:")
        for name in keep_names:
            print(f"  - {name}")
        print("\nFound survivors:")
        for name in surviving:
            print(f"  - {name}")
        print("\nWill remove:")
        if remove_names:
            for name in remove_names:
                print(f"  - {name}")
        else:
            print("  (none)")

        if not apply:
            print("\nDry run only. Re-run with --apply to make changes.")
            return 0

        backup = _backup_database(database)
        print(f"\nBackup: {backup}")

        connection.execute("BEGIN")
        for name in remove_names:
            plan_row = connection.execute(
                "SELECT id FROM generated_roster_plan WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone() if plan_names else None
            if plan_row is not None:
                connection.execute(
                    "DELETE FROM generated_roster_plan_slot WHERE plan_id = ?",
                    (int(plan_row[0]),),
                )
                connection.execute(
                    "DELETE FROM generated_roster_plan WHERE id = ?",
                    (int(plan_row[0]),),
                )

            team_row = connection.execute(
                "SELECT id FROM team WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone() if roster_names else None
            if team_row is not None:
                connection.execute(
                    "DELETE FROM team_member WHERE team_id = ?",
                    (int(team_row[0]),),
                )
                connection.execute(
                    "DELETE FROM team WHERE id = ?",
                    (int(team_row[0]),),
                )

        connection.commit()

        roster_after = _existing_names(connection, "team")
        plan_after = _existing_names(connection, "generated_roster_plan")
        remaining = sorted(set(roster_after) | set(plan_after), key=str.casefold)
        print("\nRemaining named teams:")
        for name in remaining:
            print(f"  - {name}")
        print(f"\nRemoved {len(remove_names)} named team(s). Roster people were not deleted.")
        return 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove named Roster teams and generated plans except an explicit keep-list."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Path to eso.db (defaults to BFF's canonical database).",
    )
    parser.add_argument(
        "--keep",
        action="append",
        dest="keep_names",
        help="Team name to preserve. Repeat for multiple teams.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete data. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()
    keep_names = tuple(args.keep_names or DEFAULT_KEEP)
    return prune(args.database, keep_names, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
