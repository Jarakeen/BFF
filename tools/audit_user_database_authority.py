from __future__ import annotations

"""Read-only audit of every plausible FoundryDock user database.

This tool deliberately performs no migrations, restores, copies, or writes. It exists
for the unpleasant case where a Raid Plan appears to vanish because source and frozen
launches are resolving different user-data roots.
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Make direct `python tools/audit_user_database_authority.py` execution work from
# any working directory. The older recovery tool did not do this, which is how we
# managed to add insult to a persistence incident with ModuleNotFoundError.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import get_user_database_path


@dataclass(frozen=True)
class DatabaseAudit:
    path: str
    exists: bool
    size_bytes: int
    plan_count: int
    revision_count: int
    plans: tuple[dict[str, object], ...]
    error: str | None = None


def candidate_database_paths() -> tuple[Path, ...]:
    """Return canonical plus known source/frozen locations without choosing for the user."""
    rows: list[Path] = [get_user_database_path()]
    override = str(os.environ.get("FOUNDRYDOCK_USER_DATA_DIR", "") or "").strip()
    if override:
        rows.append(Path(override).expanduser().resolve() / "foundrydock.db")

    rows.append(PROJECT_ROOT / "user_data" / "foundrydock.db")

    local = str(os.environ.get("LOCALAPPDATA", "") or "").strip()
    if local:
        rows.append(Path(local) / "FoundryDock" / "foundrydock.db")
    else:
        rows.append(Path.home() / "AppData" / "Local" / "FoundryDock" / "foundrydock.db")

    unique: list[Path] = []
    seen: set[str] = set()
    for row in rows:
        resolved = row.expanduser().resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return tuple(unique)


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def audit_database(path: str | Path) -> DatabaseAudit:
    database = Path(path).expanduser().resolve()
    if not database.is_file():
        return DatabaseAudit(str(database), False, 0, 0, 0, ())

    try:
        uri = f"{database.as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            plan_rows: list[dict[str, object]] = []
            if _table_exists(db, "raid_plan"):
                rows = db.execute(
                    "SELECT plan_id, payload_json, updated_at FROM raid_plan "
                    "ORDER BY updated_at DESC, plan_id COLLATE NOCASE"
                ).fetchall()
                for plan_id, payload_json, updated_at in rows:
                    try:
                        payload = json.loads(str(payload_json or ""))
                    except json.JSONDecodeError:
                        payload = {}
                    members = payload.get("members") if isinstance(payload, dict) else []
                    occupied = 0
                    if isinstance(members, list):
                        occupied = sum(
                            1 for member in members
                            if isinstance(member, dict)
                            and (
                                str(member.get("gamertag") or "").strip()
                                or str(member.get("character_name") or "").strip()
                            )
                        )
                    plan_rows.append(
                        {
                            "plan_id": str(plan_id or ""),
                            "name": str(payload.get("name") or "") if isinstance(payload, dict) else "",
                            "team_name": str(payload.get("team_name") or "") if isinstance(payload, dict) else "",
                            "trial_id": str(payload.get("trial_id") or "") if isinstance(payload, dict) else "",
                            "occupied_seats": occupied,
                            "updated_at": str(updated_at or ""),
                        }
                    )

            revision_count = 0
            if _table_exists(db, "raid_plan_revision"):
                revision_count = int(
                    db.execute("SELECT COUNT(*) FROM raid_plan_revision").fetchone()[0]
                )

        return DatabaseAudit(
            str(database),
            True,
            database.stat().st_size,
            len(plan_rows),
            revision_count,
            tuple(plan_rows),
        )
    except (OSError, sqlite3.Error) as exc:
        return DatabaseAudit(
            str(database),
            True,
            database.stat().st_size if database.exists() else 0,
            0,
            0,
            (),
            f"{type(exc).__name__}: {exc}",
        )


def audit_all() -> tuple[DatabaseAudit, ...]:
    return tuple(audit_database(path) for path in candidate_database_paths())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of FoundryDock user database locations."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    audits = audit_all()
    canonical = str(get_user_database_path().expanduser().resolve())
    if args.json:
        print(
            json.dumps(
                {
                    "canonical_path": canonical,
                    "databases": [asdict(row) for row in audits],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print("FOUNDRYDOCK USER DATABASE AUTHORITY AUDIT")
    print(f"Active canonical path: {canonical}")
    print("READ ONLY: no database was changed.")
    for row in audits:
        marker = "ACTIVE" if os.path.normcase(row.path) == os.path.normcase(canonical) else "alternate"
        print()
        print(f"[{marker}] {row.path}")
        print(
            f"  exists={row.exists} size={row.size_bytes} "
            f"plans={row.plan_count} revisions={row.revision_count}"
        )
        if row.error:
            print(f"  ERROR: {row.error}")
        for plan in row.plans:
            print(
                "  PLAN "
                f"{plan['plan_id']} | {plan['name']} | {plan['team_name']} | "
                f"{plan['trial_id']} | seats={plan['occupied_seats']} | "
                f"updated={plan['updated_at']}"
            )

    populated = [row for row in audits if row.exists and row.plan_count]
    if len(populated) > 1:
        print()
        print("WARNING: more than one plausible user database contains Raid Plans.")
        print("Do not restore or overwrite either database until the intended authority is confirmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
