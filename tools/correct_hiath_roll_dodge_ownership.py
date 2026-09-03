from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.reviewed_canonical_mechanic_correction import (
    HIATH_ROLL_DODGE_OWNERSHIP,
    apply_canonical_mechanic_correction,
    inspect_canonical_mechanic_correction,
)


SOURCE_PATH = ROOT / "data" / "eso_info" / "bosses" / "hiath_the_battlemaster.json"
EXPECTED_SOURCE_DESCRIPTION = "Hiath can perform a roll dodge to avoid incoming damage."


def _validate_source() -> None:
    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if payload.get("id") != "hiath_the_battlemaster":
        raise RuntimeError("Hiath source identity changed; refusing canonical correction")

    abilities = [
        row for row in payload.get("abilities", ())
        if isinstance(row, dict) and row.get("name") == "Roll Dodge"
    ]
    mechanics = [
        row for row in payload.get("mechanics", ())
        if isinstance(row, dict) and row.get("name") == "Roll Dodge"
    ]
    if len(abilities) != 1 or len(mechanics) != 1:
        raise RuntimeError(
            "Hiath source must contain exactly one Roll Dodge ability and mechanic"
        )
    if abilities[0].get("description") != EXPECTED_SOURCE_DESCRIPTION:
        raise RuntimeError("Hiath Roll Dodge ability description changed; review required")
    if mechanics[0].get("description") != EXPECTED_SOURCE_DESCRIPTION:
        raise RuntimeError("Hiath Roll Dodge mechanic description changed; review required")
    if mechanics[0].get("requires_movement") is not True:
        raise RuntimeError("Hiath Roll Dodge source movement flag changed; review required")


def _backup_database(database: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = database.with_name(
        f"{database.name}.before-hiath-roll-dodge-correction.{timestamp}"
    )
    source = sqlite3.connect(database)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup


def _post_write_audit(database: Path) -> tuple[bool, tuple[tuple[str, str], ...]]:
    service = EncounterService(
        EncounterRepository(
            ROOT / "data" / "eso_info" / "bosses",
            ROOT / "data" / "encounter_evidence",
            database_path=database,
        )
    )
    rows = tuple(
        (row.mechanic_name, row.requirement_type)
        for row in service.requirements("hiath_the_battlemaster")
    )
    return ("Roll Dodge", "movement") not in rows, rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Correct the reviewed Hiath Roll Dodge mechanic so its movement is "
            "explicitly boss-owned rather than projected as a player demand."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "eso.db",
        help="Encounter SQLite database (default: data/eso.db)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the guarded correction. Without this flag the tool is read-only.",
    )
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"Database does not exist: {database}")

    print("HIATH ROLL DODGE CANONICAL OWNERSHIP CORRECTION")
    print(f"Database: {database}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    _validate_source()
    print("PASS source says Hiath performs Roll Dodge")

    connection = sqlite3.connect(database)
    try:
        inspection = inspect_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )
    finally:
        connection.close()

    print(
        "PASS canonical target resolved: "
        f"fact_id={inspection.fact_id} fact_key={inspection.fact_key}"
    )
    print(
        "State: "
        + ("correction required" if inspection.changed else "already corrected")
    )
    print(f"Rationale: {HIATH_ROLL_DODGE_OWNERSHIP.rationale}")

    if not args.apply:
        print()
        print("RESULT: PASS (dry run; database unchanged)")
        return 0

    if not inspection.changed:
        passed, requirements = _post_write_audit(database)
        print("Backup: not created; correction was already present")
        print(f"Player requirements: {requirements}")
        print("RESULT: PASS" if passed else "RESULT: FAIL")
        return 0 if passed else 1

    backup = _backup_database(database)
    print(f"Backup created: {backup}")

    connection = sqlite3.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = apply_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    passed, requirements = _post_write_audit(database)
    print(
        "WRITE RESULT: "
        f"{'CORRECTED' if result.changed else 'ALREADY CORRECT'}"
    )
    print("Canonical requirement_subjects: movement=boss")
    print(f"Player requirements: {requirements}")
    print(
        "PASS Roll Dodge is excluded from player movement requirements"
        if passed
        else "FAIL Roll Dodge still appears as a player movement requirement"
    )
    print()
    print("RESULT: PASS" if passed else "RESULT: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
