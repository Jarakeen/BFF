from __future__ import annotations

"""Read-only verification for recovered UESP boss JSON records.

Intended for targeted encounter recovery before any eso.db import. Reports the
fields that are easiest to lose silently: all health tiers, abilities,
mechanics, phases, dialogue trigger/context coverage, and source provenance.
"""

import argparse
import json
from pathlib import Path
from typing import Any


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _load(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR {path}: {exc}")
        return None
    return payload if isinstance(payload, dict) else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clip(text: str, width: int = 120) -> str:
    text = _clean(text)
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def _health(record: dict[str, Any]) -> dict[str, Any]:
    health = _dict(record.get("health"))
    return {
        "normal": health.get("normal"),
        "veteran": health.get("veteran"),
        "hardmode": health.get("hardmode"),
    }


def _dialogue_stats(record: dict[str, Any]) -> tuple[int, int, int, list[tuple[str, int]]]:
    dialogue = _list(record.get("dialogue"))
    with_trigger = 0
    with_ability = 0
    grouped: dict[str, int] = {}

    for row in dialogue:
        if not isinstance(row, dict):
            continue
        trigger = _clean(row.get("trigger"))
        ability = _clean(row.get("ability"))
        if trigger:
            with_trigger += 1
            grouped[trigger] = grouped.get(trigger, 0) + 1
        if ability:
            with_ability += 1

    groups = sorted(grouped.items(), key=lambda item: (-item[1], item[0].casefold()))
    return len(dialogue), with_trigger, with_ability, groups


def verify_one(path: Path, record: dict[str, Any]) -> None:
    name = _clean(record.get("name")) or path.stem
    boss_id = _clean(record.get("id")) or path.stem
    content_id = _clean(record.get("content_id"))
    content_name = _clean(record.get("content_name"))
    health = _health(record)
    abilities = _list(record.get("abilities"))
    mechanics = _list(record.get("mechanics"))
    phases = _list(record.get("phases"))
    dialogue_count, dialogue_with_trigger, dialogue_with_ability, trigger_groups = _dialogue_stats(record)
    difficulty = _dict(record.get("difficulty_notes"))
    source = _dict(record.get("source"))

    print(f"--- {name} [{boss_id}] ---")
    print(f"  content:        {content_name or '(blank)'} [{content_id or 'blank'}]")
    print(f"  health normal:  {health['normal'] or '(missing)'}")
    print(f"  health veteran: {health['veteran'] or '(missing)'}")
    print(f"  health hardmode:{health['hardmode'] or '(missing)'}")
    print(f"  abilities:      {len(abilities)}")
    print(f"  mechanics:      {len(mechanics)}")
    print(f"  phases:         {len(phases)}")
    print(f"  dialogue rows:  {dialogue_count}")
    print(f"    with trigger: {dialogue_with_trigger}")
    print(f"    linked ability:{dialogue_with_ability}")
    print(f"  NV notes:       {len(_list(difficulty.get('normal_veteran_differences')))}")
    print(f"  HM notes:       {len(_list(difficulty.get('hardmode_info')))}")
    print(f"  source URL:     {_clean(source.get('url')) or '(missing)'}")
    print(f"  revision:       {source.get('revision_id') or '(missing)'}")
    print(f"  retrieved:      {_clean(source.get('retrieved_at')) or '(missing)'}")

    if trigger_groups:
        print("  dialogue trigger groups:")
        for trigger, count in trigger_groups[:12]:
            print(f"    {count:3} | {_clip(trigger)}")
        if len(trigger_groups) > 12:
            print(f"    ... {len(trigger_groups) - 12} more trigger groups")

    if abilities:
        print("  first abilities:")
        for row in abilities[:8]:
            if not isinstance(row, dict):
                continue
            print(f"    - {_clean(row.get('name')) or '(unnamed)'}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify recovered boss JSON before eso.db import")
    parser.add_argument(
        "bosses",
        nargs="+",
        help="Boss ids / JSON stems, e.g. oaxiltso flame_herald_bahsei xalvakka",
    )
    parser.add_argument("--boss-dir", default="data/uesp/bosses")
    args = parser.parse_args()

    boss_dir = Path(args.boss_dir)
    print("=" * 72)
    print(" RECOVERED ENCOUNTER VERIFICATION - READ ONLY")
    print("=" * 72)

    failures = 0
    for boss in args.bosses:
        stem = boss[:-5] if boss.lower().endswith(".json") else boss
        path = boss_dir / f"{stem}.json"
        if not path.exists():
            print(f"MISSING: {path}")
            failures += 1
            continue
        record = _load(path)
        if record is None:
            failures += 1
            continue
        verify_one(path, record)

    print("No database rows or source JSON files were changed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
