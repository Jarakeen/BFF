from __future__ import annotations

"""Read-only audit of dialogue trigger -> ability links in recovered boss JSON."""

import argparse
import json
from pathlib import Path
from typing import Any


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR {path}: {exc}")
        return None
    return value if isinstance(value, dict) else None


def clip(text: str, width: int = 86) -> str:
    text = clean(text)
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def audit(record: dict[str, Any]) -> None:
    name = clean(record.get("name")) or "(unnamed)"
    boss_id = clean(record.get("id")) or "(missing id)"
    rows = record.get("dialogue") if isinstance(record.get("dialogue"), list) else []

    grouped: dict[tuple[str, str], int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        trigger = clean(row.get("trigger")) or "(no trigger)"
        ability = clean(row.get("ability")) or "(unlinked)"
        key = (trigger, ability)
        grouped[key] = grouped.get(key, 0) + 1

    print(f"--- {name} [{boss_id}] ---")
    for (trigger, ability), count in sorted(grouped.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())):
        print(f"  {count:3} | {clip(trigger)} -> {ability}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit recovered dialogue trigger-to-ability links without changing data")
    parser.add_argument("bosses", nargs="+")
    parser.add_argument("--boss-dir", default="data/uesp/bosses")
    args = parser.parse_args()

    boss_dir = Path(args.boss_dir)
    print("=" * 76)
    print(" DIALOGUE TRIGGER -> ABILITY LINK AUDIT - READ ONLY")
    print("=" * 76)

    failures = 0
    for boss in args.bosses:
        stem = boss[:-5] if boss.lower().endswith(".json") else boss
        path = boss_dir / f"{stem}.json"
        if not path.exists():
            print(f"MISSING: {path}")
            failures += 1
            continue
        record = load(path)
        if record is None:
            failures += 1
            continue
        audit(record)

    print("No database rows or source JSON files were changed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
