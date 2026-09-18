from __future__ import annotations

"""One-time user planning-state reset for FoundryDock.

This deliberately preserves the ESO reference database schema/content while clearing
user-owned people, character/build identity, team, Comp Maker, and Raid Plan state so
the application behaves like a fresh install ready for its first team.

The reset always creates a timestamped backup before changing anything.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir


JSON_RESETS = {
    "builds.json": {"Members": []},
    "characters.json": {
        "schema_version": 4,
        "players": [],
        "characters": [],
        "builds": [],
        "team_assignments": [],
    },
    "raid_plans.json": {"schema_version": 1, "plans": []},
    "team_composition_user_templates.json": {"schema_version": 1, "templates": []},
}

# Delete dependent/evidence tables before their owning rows. Every table is optional
# because older FoundryDock databases may not contain every migration-era table.
SQLITE_CLEAR_ORDER = (
    "generated_roster_draft_recruit_prescription",
    "generated_roster_draft_slot",
    "generated_roster_draft",
    "generated_roster_legacy_assignment_evidence",
    "generated_roster_recruit_prescription",
    "generated_roster_plan_slot",
    "generated_roster_plan",
    "roster_assignment_context",
    "roster_member_assignment",
    "roster_member_availability",
    "roster_player_alias",
    "roster_recruitment_candidate",
    "roster_archive_record",
    "team_member",
    "team",
    "roster_member",
)

PRESERVED_TABLES = ()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _row_count(connection: sqlite3.Connection, table: str) -> int:
    if not _table_exists(connection, table):
        return 0
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _backup(data_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = data_dir / "reset_backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    for name in ("eso.db", *JSON_RESETS):
        source = data_dir / name
        if source.is_file():
            shutil.copy2(source, backup_dir / name)

    return backup_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def reset_user_planning_state(data_dir: Path) -> dict[str, object]:
    data_dir = Path(data_dir)
    database_path = data_dir / "eso.db"
    if not database_path.is_file():
        raise FileNotFoundError(f"FoundryDock database not found: {database_path}")

    backup_dir = _backup(data_dir)

    report: dict[str, object] = {
        "backup_dir": str(backup_dir),
        "sqlite_deleted": {},
        "preserved": {},
        "json_reset": [],
    }

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("BEGIN")
        for table in SQLITE_CLEAR_ORDER:
            if not _table_exists(connection, table):
                continue
            before = _row_count(connection, table)
            connection.execute(f'DELETE FROM "{table}"')
            report["sqlite_deleted"][table] = before
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    for name, payload in JSON_RESETS.items():
        _write_json(data_dir / name, payload)
        report["json_reset"].append(name)

    # Re-open and prove the requested state is actually empty.
    connection = sqlite3.connect(database_path)
    try:
        remaining = {
            table: _row_count(connection, table)
            for table in SQLITE_CLEAR_ORDER
            if _table_exists(connection, table)
        }
        nonzero = {table: count for table, count in remaining.items() if count}
        if nonzero:
            raise RuntimeError(f"Reset verification failed; rows remain: {nonzero}")
        report["verified_empty_tables"] = tuple(remaining)
        report["preserved_after"] = {}
    finally:
        connection.close()

    for name, expected in JSON_RESETS.items():
        actual = json.loads((data_dir / name).read_text(encoding="utf-8"))
        if actual != expected:
            raise RuntimeError(f"Reset verification failed for {name}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Back up and clear FoundryDock user people, characters, Builds, Teams, "
            "Comp drafts, Raid Plans, and planning assignments while preserving "
            "the ESO reference database schema and game data."
        )
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required acknowledgement for this destructive user-state reset.",
    )
    args = parser.parse_args()

    if not args.confirm_reset:
        parser.error("--confirm-reset is required")

    data_dir = get_data_dir()
    report = reset_user_planning_state(data_dir)

    print("FOUNDRYDOCK USER PLANNING STATE RESET")
    print(f"data_dir={data_dir}")
    print(f"backup={report['backup_dir']}")
    print("")

    print("CLEARED SQLITE ROWS")
    deleted = report["sqlite_deleted"]
    if deleted:
        for table, count in deleted.items():
            print(f"  {table}: {count}")
    else:
        print("  none")

    print("")
    print("RESET JSON FILES")
    for name in report["json_reset"]:
        print(f"  {name}")

    print("")
    print("PRESERVED")
    print("  ESO reference/game tables and database schema")

    print("")
    print("RESULT=PASS")


if __name__ == "__main__":
    main()
