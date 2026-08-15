from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Interval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def load_events(connection: sqlite3.Connection, ability_id: int) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT report_code, fight_id, event_index, timestamp, event_type,
               source_id, target_id, target_instance, ability_game_id, stack,
               raw_json
        FROM log_event
        WHERE ability_game_id = ?
          AND event_type IN (
              'applybuff', 'removebuff', 'refreshbuff',
              'applybuffstack', 'removebuffstack',
              'applydebuff', 'removedebuff', 'refreshdebuff',
              'applydebuffstack', 'removedebuffstack', 'cast'
          )
        ORDER BY report_code, fight_id, timestamp, event_index
        """,
        (ability_id,),
    ).fetchall()


def actor_names(connection: sqlite3.Connection) -> dict[tuple[str, int, int], tuple[str, str]]:
    rows = connection.execute(
        "SELECT report_code, fight_id, actor_id, name, role FROM log_actor"
    ).fetchall()
    return {
        (str(row[0]), int(row[1]), int(row[2])): (str(row[3] or f'Actor {row[2]}'), str(row[4] or 'unknown'))
        for row in rows
    }


def ability_candidates(connection: sqlite3.Connection, search: str) -> list[tuple[int, int]]:
    """Return ability IDs whose raw event payload mentions the requested text.

    The combat table intentionally preserves raw ESO Logs JSON. We use that
    evidence here rather than inventing a static ability-name mapping.
    """
    needle = search.lower()
    rows = connection.execute(
        """
        SELECT ability_game_id, COUNT(*)
        FROM log_event
        WHERE ability_game_id IS NOT NULL
          AND lower(raw_json) LIKE ?
        GROUP BY ability_game_id
        ORDER BY COUNT(*) DESC
        """,
        (f"%{needle}%",),
    ).fetchall()
    return [(int(row[0]), int(row[1])) for row in rows]


def event_name(row: sqlite3.Row) -> str:
    try:
        payload = json.loads(row["raw_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        payload = {}
    for key in ("ability", "abilityGameID", "abilityName", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return str(row["ability_game_id"])


def analyze(rows: list[sqlite3.Row]) -> dict[tuple[str, int, int, int], dict[str, Any]]:
    groups: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    open_intervals: dict[tuple[str, int, int, int], list[float]] = defaultdict(list)

    for row in rows:
        key = (
            str(row["report_code"]),
            int(row["fight_id"]),
            int(row["source_id"] if row["source_id"] is not None else -1),
            int(row["target_id"] if row["target_id"] is not None else -1),
        )
        bucket = groups.setdefault(
            key,
            {"applications": 0, "refreshes": 0, "stack_events": 0, "casts": 0, "intervals": [], "event_name": event_name(row)},
        )
        event_type = str(row["event_type"])
        timestamp = float(row["timestamp"])

        if event_type in {"applybuff", "applydebuff"}:
            bucket["applications"] += 1
            open_intervals[key].append(timestamp)
        elif event_type in {"refreshbuff", "refreshdebuff"}:
            bucket["refreshes"] += 1
        elif event_type in {"applybuffstack", "applydebuffstack", "removebuffstack", "removedebuffstack"}:
            bucket["stack_events"] += 1
        elif event_type == "cast":
            bucket["casts"] += 1
        elif event_type in {"removebuff", "removedebuff"}:
            starts = open_intervals[key]
            if starts:
                start = starts.pop(0)
                bucket["intervals"].append(Interval(start, timestamp))

    # Any still-open effect is intentionally left open. We report it as an
    # observation without inventing a removal timestamp.
    for key, starts in open_intervals.items():
        bucket = groups[key]
        bucket["open_starts"] = starts

    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ESO Logs observed-effect lifecycle analyzer")
    parser.add_argument("--db", required=True)
    parser.add_argument("--ability-id", type=int)
    parser.add_argument("--ability", help="Search raw event JSON for an ability/effect name")
    args = parser.parse_args()

    if args.ability_id is None and not args.ability:
        parser.error("provide --ability-id or --ability")

    connection = sqlite3.connect(Path(args.db))
    try:
        ability_id = args.ability_id
        if ability_id is None:
            candidates = ability_candidates(connection, args.ability)
            if not candidates:
                print(f"No event payloads matched {args.ability!r}.")
                return 1
            if len(candidates) > 1:
                print(f"Multiple ability IDs matched {args.ability!r}:")
                for candidate_id, count in candidates[:20]:
                    print(f"  {candidate_id}: {count} events")
                print("Re-run with --ability-id once the correct ID is identified.")
                return 2
            ability_id = candidates[0][0]

        rows = load_events(connection, ability_id)
        if not rows:
            print(f"No lifecycle events found for ability ID {ability_id}.")
            return 1

        names = actor_names(connection)
        groups = analyze(rows)

        print("=== Observed Effect Lifecycle ===")
        print(f"ability_id={ability_id}")
        print(f"events={len(rows)}")
        print(f"source/target groups={len(groups)}")
        print()

        for (report_code, fight_id, source_id, target_id), data in sorted(groups.items()):
            source_name, role = names.get((report_code, fight_id, source_id), (f"Actor {source_id}", "unknown"))
            closed_duration = sum(interval.duration for interval in data["intervals"])
            open_count = len(data.get("open_starts", []))
            print(f"{report_code} fight={fight_id} {source_name} ({role}) -> target={target_id}")
            print(f"  applications={data['applications']} refreshes={data['refreshes']} stack_events={data['stack_events']} casts={data['casts']}")
            print(f"  closed_duration_ms={closed_duration:.0f} open_intervals={open_count}")

        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
