from __future__ import annotations

import json
from pathlib import Path


RAW_FILES = [
    Path("data/raw/esologs_probe.json"),
    Path("data/raw/esologs_night2.json"),
]

TARGET_FIGHT_ID = "6"


def find_fight():
    for path in RAW_FILES:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        fights = data.get("fights", {})

        if not isinstance(fights, dict):
            continue

        for fight_id, fight in fights.items():
            if str(fight_id) == TARGET_FIGHT_ID:
                return path, data.get("report_code"), fight_id, fight

    return None


def main() -> None:
    result = find_fight()

    if result is None:
        print(
            f"Could not find fight {TARGET_FIGHT_ID} "
            "in any configured raw ESO Logs file."
        )
        return

    path, report_code, fight_id, fight = result

    print("=" * 80)
    print("LOKKESTIIZ COMBATANT INFO")
    print("=" * 80)
    print(f"Source file: {path}")
    print(f"Report code: {report_code}")
    print(f"Fight ID:    {fight_id}")
    print()

    events = fight.get("events", [])

    if isinstance(events, dict):
        for key in ("data", "events", "results"):
            if isinstance(events.get(key), list):
                events = events[key]
                break

    if not isinstance(events, list):
        print(
            "Events are not a list."
        )
        print(
            f"Actual type: {type(events).__name__}"
        )
        return

    combatants = [
        event
        for event in events
        if event.get("type") == "combatantinfo"
    ]

    print(
        f"Combatant records: {len(combatants)}"
    )
    print()

    for index, event in enumerate(
        combatants,
        start=1,
    ):
        print("=" * 80)
        print(f"COMBATANT {index}")
        print("=" * 80)

        print(
            json.dumps(
                event,
                indent=2,
                ensure_ascii=False,
            )
        )

        print()


if __name__ == "__main__":
    main()