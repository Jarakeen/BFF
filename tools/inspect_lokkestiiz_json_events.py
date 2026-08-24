"""
tools/inspect_lokkestiiz_json_events.py

Diagnostic script for the ESO Logs JSON adapter
(services/esologs_json_adapter.py).

Reads a fight directly from a raw ESO Logs JSON export
(data/raw/esologs_night2.json by default) and prints:

    - fight metadata
    - total events
    - event types (raw ESO Logs type -> count)
    - top ability IDs
    - first 20 normalized SemanticCombatEvents

This is a read-only inspection tool. It does not write anything, and
it does not interpret game mechanics - it only shows what the JSON
adapter + existing SemanticCombatEvent classification produce.

Usage:

    python tools/inspect_lokkestiiz_json_events.py
    python tools/inspect_lokkestiiz_json_events.py --fight-id 27
    python tools/inspect_lokkestiiz_json_events.py --path data/raw/esologs_probe.json --fight-id 41
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from services.esologs_json_adapter import (
    DEFAULT_RAW_PATH,
    EsoLogsJsonEventInterpreter,
    EsoLogsJsonFight,
    EsoLogsJsonFightNotFoundError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a fight from a raw ESO Logs JSON export via the "
            "JSON adapter."
        ),
    )

    parser.add_argument(
        "--fight-id",
        type=int,
        default=6,
        help="Fight id to inspect (default: 6, the Lokkestiiz kill).",
    )

    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help=(
            "Path to the raw ESO Logs JSON export "
            f"(default: {DEFAULT_RAW_PATH})."
        ),
    )

    parser.add_argument(
        "--top-abilities",
        type=int,
        default=25,
        help="How many top ability ids to print (default: 25).",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help=(
            "How many normalized SemanticCombatEvents to print "
            "(default: 20)."
        ),
    )

    return parser.parse_args()


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_fight_metadata(fight: EsoLogsJsonFight) -> None:
    print_header("FIGHT METADATA")

    print(f"Report code:     {fight.report_code}")
    print(f"Fight id:        {fight.fight_id}")
    print(f"Name:            {fight.name}")
    print(f"Encounter ID:    {fight.encounter_id}")
    print(f"Kill:            {fight.kill}")
    print(f"Difficulty:      {fight.difficulty}")
    print(f"Start time:      {fight.start_time}")
    print(f"End time:        {fight.end_time}")
    print(f"Declared count:  {fight.declared_event_count}")
    print(f"Actual events:   {fight.event_count}")

    if fight.declared_event_count is not None:
        matches = fight.declared_event_count == fight.event_count
        print(f"Counts match:    {matches}")


def print_event_types(events) -> None:
    print_header("EVENT TYPES (raw ESO Logs type)")

    counts = Counter(event.raw_event_type for event in events)

    for event_type, count in counts.most_common():
        print(f"{event_type:30} {count:,}")

    print()
    print("Semantic kinds (after classify_event):")
    print("-" * 78)

    semantic_counts = Counter(event.event_kind for event in events)

    for kind, count in semantic_counts.most_common():
        print(f"{kind:25} {count:,}")


def print_top_abilities(events, limit: int) -> None:
    print_header(f"TOP {limit} ABILITY IDS")

    abilities = Counter(
        event.ability_game_id
        for event in events
        if event.ability_game_id is not None
    )

    for ability_id, count in abilities.most_common(limit):
        print(f"{str(ability_id):15} {count:,}")


def print_sample_events(events, limit: int) -> None:
    print_header(f"FIRST {limit} NORMALIZED SemanticCombatEvents")

    for event in events[:limit]:
        print(
            f"[{event.event_index:>6}] "
            f"t={event.timestamp:>10.0f} "
            f"kind={event.event_kind:18} "
            f"raw_type={event.raw_event_type:16} "
            f"src={str(event.source_id):>6} "
            f"tgt={str(event.target_id):>6} "
            f"ability={str(event.ability_game_id):>8} "
            f"name={event.ability_name}"
        )


def main() -> None:
    args = parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}")
        print(
            "data/raw/ is gitignored in this project - place the "
            "export there before running this script."
        )
        return

    try:
        fight = EsoLogsJsonFight.load(args.path, fight_id=args.fight_id)
    except EsoLogsJsonFightNotFoundError as exc:
        print(f"Error: {exc}")
        return

    interpreter = EsoLogsJsonEventInterpreter(fight)

    events = list(interpreter.iter_events())

    print_fight_metadata(fight)

    print_header("TOTAL EVENTS")
    print(f"{len(events):,}")

    print_event_types(events)
    print_top_abilities(events, args.top_abilities)
    print_sample_events(events, args.sample_size)


if __name__ == "__main__":
    main()
