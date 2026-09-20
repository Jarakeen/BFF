from __future__ import annotations

"""Fail a packaged FoundryDock first-install artifact if developer user state leaked in."""

import argparse
import json
from pathlib import Path
import sqlite3


USER_TABLE_PREFIXES = (
    "roster_",
    "generated_roster_",
    "stickerbook_",
    "log_",
)
EXACT_USER_TABLES = {
    "team",
    "team_member",
    "collectible_profile",
    "collectible_progress",
    "collectible_rumor_progress",
}


def _user_tables(db: sqlite3.Connection) -> tuple[str, ...]:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names = [str(row[0]) for row in rows]
    return tuple(
        name for name in names
        if name in EXACT_USER_TABLES or any(name.startswith(prefix) for prefix in USER_TABLE_PREFIXES)
    )


def _count(db: sqlite3.Connection, table: str) -> int:
    escaped = table.replace('"', '""')
    return int(db.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0])


def audit(package_root: Path) -> list[str]:
    package_root = Path(package_root)
    errors: list[str] = []
    data = package_root / "data"
    db_path = data / "eso.db"
    if not db_path.is_file():
        return [f"missing packaged database: {db_path}"]

    with sqlite3.connect(db_path) as db:
        for table in _user_tables(db):
            rows = _count(db, table)
            if rows:
                errors.append(f"packaged user-state table is not empty: {table} ({rows} row(s))")

    characters = data / "characters.json"
    if not characters.is_file():
        errors.append(f"missing clean identity file: {characters}")
    else:
        payload = json.loads(characters.read_text(encoding="utf-8"))
        for key in ("players", "characters", "builds", "team_assignments"):
            rows = payload.get(key, [])
            if rows:
                errors.append(f"packaged characters.json has non-empty {key}: {len(rows)} row(s)")

    builds = data / "builds.json"
    if not builds.is_file():
        errors.append(f"missing clean builds file: {builds}")
    else:
        payload = json.loads(builds.read_text(encoding="utf-8"))
        members = payload.get("Members", [])
        if members:
            errors.append(f"packaged builds.json has non-empty Members: {len(members)} row(s)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    args = parser.parse_args()

    errors = audit(args.package_root)
    if errors:
        print("RELEASE PRIVACY AUDIT: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1

    print("RELEASE PRIVACY AUDIT: PASS")
    print(f"  package_root={args.package_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
