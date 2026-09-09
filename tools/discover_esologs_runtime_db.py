from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir

_REQUIRED_TABLES = ("log_fight", "log_actor", "log_event")
_SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def _table_names(path: Path) -> tuple[str, ...]:
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return ()
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)
    except sqlite3.Error:
        return ()
    finally:
        connection.close()


def discover(*, roots: tuple[Path, ...]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    matches: list[Path] = []
    for root in roots:
        root = root.resolve()
        if not root.exists():
            continue
        candidates = (root,) if root.is_file() else tuple(
            path for path in root.rglob("*")
            if path.is_file() and path.suffix.casefold() in _SQLITE_SUFFIXES
        )
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            tables = set(_table_names(resolved))
            if all(name in tables for name in _REQUIRED_TABLES):
                matches.append(resolved)
    return tuple(sorted(matches, key=lambda path: str(path).casefold()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find SQLite databases that contain the ESO Logs runtime tables."
    )
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Optional files/directories to scan. Defaults to project data and user_data.",
    )
    args = parser.parse_args()

    roots = tuple(args.roots) or (
        get_data_dir(),
        ROOT / "data",
        ROOT / "user_data",
        ROOT / "research",
    )
    matches = discover(roots=roots)

    print("ESO LOGS RUNTIME DATABASE DISCOVERY")
    print("SCAN_ROOTS:")
    for root in roots:
        print(f"- {root}")
    print(f"MATCH_COUNT: {len(matches)}")
    for path in matches:
        print(f"MATCH: {path}")

    if not matches:
        print("RESULT: no SQLite database with log_fight, log_actor, and log_event was found")
        return 1
    if len(matches) > 1:
        print("RESULT: multiple runtime databases found; choose one explicitly with --database")
        return 2

    print(f"RESULT: use --database \"{matches[0]}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
