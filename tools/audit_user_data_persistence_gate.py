from __future__ import annotations

"""Read-only pre-EXE persistence/Pydantic gate for user-owned FoundryDock state."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_user_database_path
from services.raid_plan_pydantic_schema import validate_raid_plan_payload
from services.user_build_catalog_pydantic_schema import validate_user_build_catalog_payload


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as db:
        return {
            str(row[0])
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--duplicate-name",
        action="append",
        default=[],
        help="Report exact Personnel/character labels for manual identity reconciliation.",
    )
    args = parser.parse_args(argv)

    path = get_user_database_path()
    if not path.is_file():
        raise RuntimeError(f"User database does not exist: {path}")
    before = _digest(path)
    tables = _tables(path)

    required = {"build_catalog", "raid_plan", "roster_member", "team"}
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError(f"Missing canonical user-data table(s): {', '.join(missing)}")

    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        catalog_row = db.execute(
            "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
        ).fetchone()
        if catalog_row is None:
            raise RuntimeError("Canonical Build catalog row is missing")
        try:
            catalog = validate_user_build_catalog_payload(
                json.loads(str(catalog_row["payload_json"] or ""))
            )
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Canonical Build catalog failed strict validation: {exc}") from exc

        raid_rows = db.execute(
            "SELECT plan_id, payload_json FROM raid_plan ORDER BY plan_id COLLATE NOCASE"
        ).fetchall()
        raid_plans = []
        for row in raid_rows:
            try:
                payload = validate_raid_plan_payload(
                    json.loads(str(row["payload_json"] or ""))
                )
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Raid Plan {row['plan_id']!r} failed strict validation: {exc}"
                ) from exc
            if str(payload.get("plan_id") or "").casefold() != str(row["plan_id"] or "").casefold():
                raise RuntimeError(
                    f"Raid Plan row identity does not match payload: {row['plan_id']!r}"
                )
            raid_plans.append(payload)

        members = db.execute(
            "SELECT id, player_name, character_name FROM roster_member ORDER BY id"
        ).fetchall()
        teams = db.execute(
            "SELECT id, name FROM team ORDER BY name COLLATE NOCASE"
        ).fetchall()

    after = _digest(path)
    if after != before:
        raise RuntimeError(
            "READ-ONLY GATE FAILED: audit changed foundrydock.db. "
            "Do not build an EXE from this state."
        )

    print("FOUNDRYDOCK USER-DATA PERSISTENCE GATE")
    print(f"DB: {path}")
    print(f"SHA256: {before}")
    print(f"Saved Raid Plans: {len(raid_plans)}")
    print(f"Personnel records: {len(members)}")
    print(f"Teams: {len(teams)}")
    print(f"Canonical Players: {len(catalog['players'])}")
    print(f"Canonical Characters: {len(catalog['characters'])}")
    print(f"Canonical Builds: {len(catalog['builds'])}")

    requested = {name.strip().casefold() for name in args.duplicate_name if name.strip()}
    if requested:
        print("IDENTITY REVIEW")
        for name in sorted(requested):
            personnel = [
                member for member in members
                if str(member["player_name"] or "").strip().casefold() == name
            ]
            characters = [
                row for row in catalog["characters"]
                if str(row.get("name") or "").strip().casefold() == name
                or str(row.get("gamertag") or "").strip().casefold() == name
            ]
            print(
                f"  {name}: personnel={len(personnel)} characters={len(characters)} "
                "(report only; no automatic merge)"
            )

    print("READ-ONLY PYDANTIC/PERSISTENCE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
