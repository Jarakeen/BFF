from __future__ import annotations

"""Read-only reviewed Lokkestiiz flight-boundary audit for a local ESO Logs corpus.

This tool reuses the existing reviewed boundary service. Numeric ESO Logs ability IDs
remain evidence signatures only and are never promoted to canonical mechanic identity.
It reads one local corpus fight, resolves the observed primary hostile target from
friendly-player damage, then asks PerformanceRaidReviewLokkestiizBoundaryService for
Aerial Onslaught begin/end boundaries.

Usage:

    python tools/audit_lokkestiiz_reviewed_flight_boundaries.py \
        --report btZpy9j6KzYXkRL3 --fight-id 6
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.performance_raid_review_lokkestiiz_boundary_service import (
    PerformanceRaidReviewLokkestiizBoundaryService,
)
from tools.audit_lokkestiiz_strategy_corpus import DEFAULT_PATH, _number, _role_roster
from tools.audit_lokkestiiz_strategy_timeline import (
    _events,
    _metadata,
    _observed_primary_target,
    _player_ids,
    _selected_fight,
    _start_ms,
)


def _format_clock(seconds: float) -> str:
    minutes, remainder = divmod(max(0.0, float(seconds)), 60.0)
    return f"{int(minutes)}:{remainder:05.2f}"


def _paired_windows(boundaries) -> tuple[tuple[int, float, float], ...]:
    begins: dict[int, float] = {}
    ends: dict[int, float] = {}
    for boundary in boundaries:
        if boundary.boundary == "begin":
            begins[int(boundary.occurrence)] = float(boundary.time_seconds)
        elif boundary.boundary == "end":
            ends[int(boundary.occurrence)] = float(boundary.time_seconds)

    rows: list[tuple[int, float, float]] = []
    for occurrence in sorted(set(begins) | set(ends)):
        if occurrence in begins and occurrence in ends:
            rows.append((occurrence, begins[occurrence], ends[occurrence]))
    return tuple(rows)


def build_output(
    payload: dict[str, Any],
    *,
    report_code: str,
    fight_id: int,
) -> str:
    fight = _selected_fight(payload, report_code=report_code, fight_id=fight_id)
    events = _events(fight)
    metadata = _metadata(fight)
    roster = _role_roster(fight)
    players = _player_ids(roster)
    start_ms = _start_ms(metadata, events)

    primary_target, primary_damage, ranking = _observed_primary_target(events, players)

    lines: list[str] = []
    lines.append("LOKKESTIIZ REVIEWED FLIGHT-BOUNDARY AUDIT")
    lines.append("=" * 43)
    lines.append(f"Report: {report_code}")
    lines.append(f"Fight: {fight_id}")
    lines.append(f"Kill: {metadata.get('kill')}")
    lines.append(f"Difficulty: {metadata.get('difficulty')}")
    lines.append(f"Resolved players: {len(players)}")
    lines.append(f"Observed primary hostile target: {primary_target}")
    lines.append(f"Observed primary-target damage: {primary_damage:,.0f}")

    if primary_target is None:
        lines.append("")
        lines.append("UNRESOLVED")
        lines.append("No observed primary hostile target could be resolved from friendly damage.")
        return "\n".join(lines)

    service = PerformanceRaidReviewLokkestiizBoundaryService()
    result = service.extract(
        events,
        boss_actor_id=primary_target,
        fight_start_time_ms=start_ms,
        evidence_source=f"ESO Logs {report_code} fight {fight_id}",
    )

    lines.append("")
    lines.append("REVIEWED AERIAL ONSLAUGHT BOUNDARIES")
    lines.append("-" * 43)
    if not result.boundaries:
        lines.append("No reviewed flight boundaries resolved.")
    else:
        for boundary in result.boundaries:
            lines.append(
                f"flight={boundary.occurrence} | {boundary.boundary:5} | "
                f"t={boundary.time_seconds:7.2f}s | {_format_clock(boundary.time_seconds)}"
            )

    windows = _paired_windows(result.boundaries)
    lines.append("")
    lines.append("PAIRED FLIGHT WINDOWS")
    lines.append("-" * 43)
    if not windows:
        lines.append("No complete begin/end flight windows resolved.")
    else:
        for occurrence, begin, end in windows:
            lines.append(
                f"flight={occurrence} | begin={begin:7.2f}s | end={end:7.2f}s | "
                f"duration={end - begin:6.2f}s | {_format_clock(begin)} -> {_format_clock(end)}"
            )

    lines.append("")
    lines.append("UNRESOLVED REVIEW ITEMS")
    lines.append("-" * 43)
    if result.unresolved:
        lines.extend(result.unresolved)
    else:
        lines.append("None.")

    lines.append("")
    lines.append("NOTE: flight entry uses reviewed ESO Logs evidence signatures already tracked by")
    lines.append("BFF. Flight end is the first positive boss damage after the guarded airborne gap.")
    lines.append("These are observed runtime boundaries for this fight, not universal fixed timings.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve reviewed Lokkestiiz Aerial Onslaught boundaries from one local corpus fight."
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--report", required=True)
    parser.add_argument("--fight-id", type=int, required=True)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}")
        return 2

    with args.path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        print("Expected a JSON object at the top level.")
        return 2

    try:
        print(build_output(payload, report_code=args.report, fight_id=args.fight_id))
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
