from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class Interval:
    start: float
    end: float | None = None

    @property
    def duration(self) -> float:
        return max(0.0, (self.end if self.end is not None else self.start) - self.start)


def _json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ability_text(event: dict[str, Any]) -> str:
    candidates = (
        event.get("abilityName"),
        event.get("ability_name"),
        event.get("ability"),
        event.get("name"),
    )
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for key in ("name", "nameEnglish", "displayName"):
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def _event_with_raw(row: sqlite3.Row) -> dict[str, Any]:
    event = _json(row["raw_json"])
    event.setdefault("timestamp", row["timestamp"])
    event.setdefault("event_type", row["event_type"])
    event.setdefault("sourceID", row["source_id"])
    event.setdefault("targetID", row["target_id"])
    event.setdefault("abilityGameID", row["ability_game_id"])
    return event


def _resolve_ability_ids(conn: sqlite3.Connection, term: str) -> set[int]:
    if term.isdigit():
        return {int(term)}

    ids: set[int] = set()
    rows = conn.execute(
        "SELECT ability_game_id, raw_json FROM log_event WHERE ability_game_id IS NOT NULL"
    ).fetchall()
    needle = term.casefold()
    for row in rows:
        event = _json(row["raw_json"])
        text = _ability_text(event)
        if needle in text.casefold():
            ids.add(int(row["ability_game_id"]))
    return ids


def _load_damage_windows(conn: sqlite3.Connection) -> dict[tuple[str, int], list[tuple[float, float]]]:
    result: dict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
    rows = conn.execute(
        """
        SELECT report_code, fight_id, start_time, end_time
        FROM log_observed_damage_window
        ORDER BY report_code, fight_id, window_index
        """
    ).fetchall()
    for row in rows:
        result[(row["report_code"], int(row["fight_id"]))].append(
            (float(row["start_time"]), float(row["end_time"]))
        )
    return result


def _window_overlap(interval: tuple[float, float], windows: list[tuple[float, float]]) -> float:
    start, end = interval
    if end <= start:
        return 0.0
    return sum(max(0.0, min(end, w_end) - max(start, w_start)) for w_start, w_end in windows)


def _actor_name(row: sqlite3.Row) -> str:
    name = row["name"]
    display = row["display_name"]
    if name and name != "nil":
        return str(name)
    return str(display or f"Actor {row['actor_id']}")


def analyze(conn: sqlite3.Connection, ability_term: str) -> int:
    conn.row_factory = sqlite3.Row
    ability_ids = _resolve_ability_ids(conn, ability_term)
    if not ability_ids:
        print(f"No ability IDs matched: {ability_term}")
        return 1

    print("=== Observed Capability Analyzer ===")
    print(f"Query: {ability_term}")
    print(f"Ability IDs: {', '.join(map(str, sorted(ability_ids)))}")
    print()

    windows = _load_damage_windows(conn)
    events = conn.execute(
        """
        SELECT report_code, fight_id, event_index, timestamp, event_type,
               source_id, target_id, ability_game_id, raw_json
        FROM log_event
        WHERE ability_game_id IN ({})
          AND event_type IN ('applybuff', 'removebuff', 'applybuffstack',
                             'removebuffstack', 'refreshbuff', 'applydebuff',
                             'removedebuff', 'applydebuffstack', 'removedebuffstack',
                             'cast')
        ORDER BY report_code, fight_id, timestamp, event_index
        """.format(",".join("?" for _ in ability_ids)),
        tuple(sorted(ability_ids)),
    ).fetchall()

    actor_rows = conn.execute(
        """
        SELECT report_code, fight_id, actor_id, name, display_name, role
        FROM log_actor
        """
    ).fetchall()
    actors = {
        (r["report_code"], int(r["fight_id"]), int(r["actor_id"])): r
        for r in actor_rows
    }

    # Buff/debuff lifecycle is kept deliberately evidence-first. We pair an
    # application with the next removal/refresh for the same source/target.
    open_intervals: dict[tuple[str, int, int | None, int | None], list[Interval]] = defaultdict(list)
    completed: dict[tuple[str, int, int | None, int | None], list[Interval]] = defaultdict(list)
    casts: defaultdict[tuple[str, int, int | None], int] = defaultdict(int)
    targets: defaultdict[tuple[str, int, int | None], set[int]] = defaultdict(set)

    apply_types = {"applybuff", "applybuffstack", "refreshbuff", "applydebuff", "applydebuffstack"}
    remove_types = {"removebuff", "removebuffstack", "removedebuff", "removedebuffstack"}

    for row in events:
        event = _event_with_raw(row)
        key = (
            row["report_code"],
            int(row["fight_id"]),
            row["source_id"],
            row["target_id"],
        )
        event_type = row["event_type"]
        timestamp = float(row["timestamp"])
        if row["target_id"] is not None:
            targets[(row["report_code"], int(row["fight_id"]), row["source_id"])].add(int(row["target_id"]))

        if event_type == "cast":
            casts[(row["report_code"], int(row["fight_id"]), row["source_id"])] += 1
        elif event_type in apply_types:
            if event_type == "refreshbuff" and open_intervals[key]:
                interval = open_intervals[key].pop()
                interval.end = timestamp
                completed[key].append(interval)
            open_intervals[key].append(Interval(timestamp))
        elif event_type in remove_types and open_intervals[key]:
            interval = open_intervals[key].pop(0)
            interval.end = timestamp
            completed[key].append(interval)

    # Close still-open effects at the last relevant event in each fight.
    last_time: dict[tuple[str, int], float] = {}
    for row in events:
        key = (row["report_code"], int(row["fight_id"]))
        last_time[key] = max(last_time.get(key, 0.0), float(row["timestamp"]))
    for key, intervals in open_intervals.items():
        fight_key = (key[0], key[1])
        for interval in intervals:
            interval.end = last_time.get(fight_key, interval.start)
            completed[key].append(interval)

    grouped: dict[tuple[str, int, int | None], list[Interval]] = defaultdict(list)
    raw_target_counts: dict[tuple[str, int, int | None], set[int]] = defaultdict(set)
    for (report_code, fight_id, source_id, target_id), intervals in completed.items():
        grouped[(report_code, fight_id, source_id)].extend(intervals)
        if target_id is not None:
            raw_target_counts[(report_code, fight_id, source_id)].add(int(target_id))

    for key in sorted(grouped):
        report_code, fight_id, source_id = key
        actor = actors.get((report_code, fight_id, int(source_id))) if source_id is not None else None
        actor_label = _actor_name(actor) if actor else (f"Actor {source_id}" if source_id is not None else "Unknown source")
        role = actor["role"] if actor else "unknown"
        intervals = grouped[key]
        raw_duration = sum(i.duration for i in intervals)
        damage_windows = windows.get((report_code, fight_id), [])
        relevant_duration = sum(_window_overlap((i.start, i.end or i.start), damage_windows) for i in intervals)
        total_window_duration = sum(max(0.0, end - start) for start, end in damage_windows)
        raw_span = 0.0
        if intervals:
            raw_span = max(i.end or i.start for i in intervals) - min(i.start for i in intervals)
        raw_uptime = (raw_duration / raw_span * 100.0) if raw_span > 0 else 0.0
        relevant_uptime = (relevant_duration / total_window_duration * 100.0) if total_window_duration > 0 else 0.0
        print(f"{report_code} fight={fight_id} source={source_id} {actor_label!r} role={role}")
        print(f"  applications/intervals: {len(intervals)}")
        print(f"  targets: {len(raw_target_counts[key])}")
        print(f"  observed duration: {raw_duration / 1000.0:.2f}s")
        print(f"  raw-span uptime: {raw_uptime:.1f}%")
        print(f"  damage-window overlap: {relevant_duration / 1000.0:.2f}s")
        print(f"  damage-window uptime: {relevant_uptime:.1f}%")
        print(f"  casts matching ability ID: {casts.get(key, 0)}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze observed ESO Logs buff/debuff evidence without modifying the database.")
    parser.add_argument("--db", required=True, help="Path to ESO SQLite database")
    parser.add_argument("--ability", required=True, help="Ability name fragment or numeric abilityGameID")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        return analyze(conn, args.ability)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
