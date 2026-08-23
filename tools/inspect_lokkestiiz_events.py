from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from services.esologs_event_interpreter import (
    EsoLogsEventInterpreter,
    SemanticEventKind,
)


DB_PATH = Path("data/eso.db")

REPORT_CODE = "PCBxhWranVctf8Q2"
FIGHT_ID = 35


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    interpreter = EsoLogsEventInterpreter(connection)

    events = list(
        interpreter.iter_fight(
            REPORT_CODE,
            FIGHT_ID,
        )
    )

    print()
    print("=" * 70)
    print("ESO LOGS SEMANTIC EVENT INSPECTION")
    print("=" * 70)
    print(f"Report: {REPORT_CODE}")
    print(f"Fight:  {FIGHT_ID}")
    print(f"Events: {len(events):,}")
    print()

    # --------------------------------------------------------
    # Semantic event counts
    # --------------------------------------------------------

    print("SEMANTIC EVENT TYPES")
    print("-" * 70)

    counts = Counter(
        event.event_kind
        for event in events
    )

    for kind, count in counts.most_common():
        print(f"{kind:25} {count:,}")

    # --------------------------------------------------------
    # Raw event types
    # --------------------------------------------------------

    print()
    print("RAW ESO LOG EVENT TYPES")
    print("-" * 70)

    raw_counts = Counter(
        event.raw_event_type
        for event in events
    )

    for event_type, count in raw_counts.most_common():
        print(f"{event_type:25} {count:,}")

    # --------------------------------------------------------
    # Ability IDs
    # --------------------------------------------------------

    print()
    print("MOST COMMON ABILITY IDS")
    print("-" * 70)

    abilities = Counter(
        event.ability_game_id
        for event in events
        if event.ability_game_id is not None
    )

    for ability_id, count in abilities.most_common(50):
        print(f"{str(ability_id):15} {count:,}")

    # --------------------------------------------------------
    # Named abilities
    # --------------------------------------------------------

    named = Counter(
        event.ability_name
        for event in events
        if event.ability_name
    )

    print()
    print("ABILITY NAMES AVAILABLE IN RAW EVENTS")
    print("-" * 70)

    for name, count in named.most_common(50):
        print(f"{name:40} {count:,}")

    # --------------------------------------------------------
    # Buff/debuff sample
    # --------------------------------------------------------

    aura_events = [
        event
        for event in events
        if event.event_kind in {
            SemanticEventKind.BUFF_APPLIED,
            SemanticEventKind.BUFF_REFRESHED,
            SemanticEventKind.BUFF_REMOVED,
            SemanticEventKind.DEBUFF_APPLIED,
            SemanticEventKind.DEBUFF_REFRESHED,
            SemanticEventKind.DEBUFF_REMOVED,
        }
    ]

    print()
    print("AURA EVENTS")
    print("-" * 70)
    print(f"Total aura events: {len(aura_events):,}")

    for event in aura_events[:100]:
        print(
            f"{event.timestamp:12.0f} "
            f"{event.event_kind:20} "
            f"source={str(event.source_id):>5} "
            f"target={str(event.target_id):>5} "
            f"ability={str(event.ability_game_id):>8} "
            f"name={event.ability_name}"
        )

    connection.close()


if __name__ == "__main__":
    main()
    