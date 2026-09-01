from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.paths import NORMALIZED, RAW_DATA


RAW_FILES = [
    RAW_DATA / "esologs_probe.json",
    RAW_DATA / "esologs_night2.json",
]

OUTPUT_DIR = NORMALIZED / "lokkestiiz"

BOSS_NAME = "Lokkestiiz"
TARGET_FIGHTS = {"6", "27", "41"}


def load_json(path: Path) -> dict[str, Any]:
    print(f"Reading {path} ...")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_fights(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    fights = data.get("fights", {})
    if not isinstance(fights, dict):
        return []
    return [
        (str(fight_id), fight)
        for fight_id, fight in fights.items()
        if isinstance(fight, dict)
    ]


def fight_name(fight: dict[str, Any]) -> str:
    return str(
        fight.get("name")
        or fight.get("encounterName")
        or fight.get("bossName")
        or ""
    )


def is_lokkestiiz(fight: dict[str, Any]) -> bool:
    return BOSS_NAME.lower() in fight_name(fight).lower()


def get_events(fight: dict[str, Any]) -> list[dict[str, Any]]:
    events = fight.get("events")
    if isinstance(events, list):
        return [event for event in events if isinstance(event, dict)]
    if isinstance(events, dict):
        for key in ("data", "events", "results"):
            value = events.get(key)
            if isinstance(value, list):
                return [event for event in value if isinstance(event, dict)]
    return []


def get_players(fight: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("players", "combatants", "actors"):
        value = fight.get(key)
        if isinstance(value, list):
            return [player for player in value if isinstance(player, dict)]
    return []


def normalize_event(
    event: dict[str, Any],
    fight_start: int | float,
) -> dict[str, Any]:
    normalized = dict(event)
    timestamp = event.get("timestamp")
    if isinstance(timestamp, (int, float)):
        normalized["timestamp"] = timestamp
        normalized["relative_ms"] = timestamp - fight_start
    return normalized


def normalize_fight(
    report_code: str,
    fight_id: str,
    fight: dict[str, Any],
    source_file: Path,
) -> dict[str, Any]:
    start = fight.get("startTime")
    if not isinstance(start, (int, float)):
        start = fight.get("start")
    if not isinstance(start, (int, float)):
        start = 0

    end = fight.get("endTime")
    if not isinstance(end, (int, float)):
        end = fight.get("end")

    events = get_events(fight)
    normalized_events = [normalize_event(event, start) for event in events]

    event_types = Counter(
        str(event.get("type", "<missing>")) for event in normalized_events
    )
    abilities = Counter(
        str(event.get("abilityGameID") or event.get("ability") or "<missing>")
        for event in normalized_events
        if event.get("abilityGameID") is not None or event.get("ability") is not None
    )
    sources = {
        event.get("sourceID")
        for event in normalized_events
        if event.get("sourceID") is not None
    }
    targets = {
        event.get("targetID")
        for event in normalized_events
        if event.get("targetID") is not None
    }

    return {
        "schema_version": 1,
        "source": {
            "file": str(source_file),
            "report_code": report_code,
        },
        "fight": {
            "id": fight_id,
            "name": fight_name(fight),
            "encounterID": fight.get("encounterID"),
            "difficulty": fight.get("difficulty"),
            "startTime": start,
            "endTime": end,
            "duration_ms": end - start if isinstance(end, (int, float)) else None,
            "kill": fight.get("kill"),
            "bossPercentage": fight.get("bossPercentage"),
        },
        "players": get_players(fight),
        "events": normalized_events,
        "summary": {
            "event_count": len(normalized_events),
            "event_types": dict(event_types),
            "unique_abilities": len(abilities),
            "unique_sources": len(sources),
            "unique_targets": len(targets),
            "top_abilities": [
                {"ability": ability, "count": count}
                for ability, count in abilities.most_common(50)
            ],
        },
    }


def print_summary(result: dict[str, Any]) -> None:
    fight = result["fight"]
    summary = result["summary"]

    print()
    print("=" * 80)
    print("LOKKESTIIZ NORMALIZATION")
    print("=" * 80)
    print(f"Fight ID:       {fight.get('id')}")
    print(f"Encounter:      {fight.get('name')}")
    print(f"Encounter ID:   {fight.get('encounterID')}")
    print(f"Difficulty:     {fight.get('difficulty')}")
    print(f"Duration:       {fight.get('duration_ms')} ms")
    print(f"Events:         {summary['event_count']:,}")
    print(f"Players:        {len(result['players'])}")
    print(f"Abilities:      {summary['unique_abilities']}")
    print(f"Sources:        {summary['unique_sources']}")
    print(f"Targets:        {summary['unique_targets']}")

    print()
    print("EVENT TYPES")
    print("-" * 80)
    for event_type, count in sorted(
        summary["event_types"].items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"{event_type:30} {count:,}")

    print()
    print("TOP ABILITIES")
    print("-" * 80)
    for item in summary["top_abilities"]:
        print(f"{str(item['ability']):20} {item['count']:,}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    found = 0

    for raw_file in RAW_FILES:
        if not raw_file.exists():
            print(f"Skipping missing file: {raw_file}")
            continue

        data = load_json(raw_file)
        report_code = str(data.get("report_code", ""))
        fights = find_fights(data)
        print(f"Found {len(fights)} fights in {raw_file}")

        for fight_id, fight in fights:
            if fight_id not in TARGET_FIGHTS:
                continue

            found += 1
            result = normalize_fight(report_code, fight_id, fight, raw_file)
            output_path = OUTPUT_DIR / f"{report_code}_fight_{fight_id}.json"

            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, ensure_ascii=False)

            print_summary(result)
            print()
            print(f"Wrote: {output_path}")

    print()
    print("=" * 80)
    print(f"Target fights extracted: {found}")
    print("=" * 80)


if __name__ == "__main__":
    main()
