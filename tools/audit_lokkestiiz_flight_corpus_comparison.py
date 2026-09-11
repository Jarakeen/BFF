from __future__ import annotations

"""Compare reviewed Lokkestiiz flight windows across successful corpus kills.

Read-only research tooling. The local ESO Logs corpus remains under research/raw.
This audit reuses the existing reviewed Lokkestiiz boundary/window services and the
single-window summarizer. It reports observed distributions across successful kills
without promoting any observed clock or pressure value into canonical mechanics.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.performance_raid_review_lokkestiiz_boundary_service import (
    PerformanceRaidReviewLokkestiizBoundaryService,
)
from services.performance_raid_review_lokkestiiz_window_service import (
    PerformanceRaidReviewLokkestiizWindowService,
)
from tools.audit_lokkestiiz_flight_strategy_windows import _summarize_window
from tools.audit_lokkestiiz_strategy_corpus import DEFAULT_PATH, _fight_rows, _role_roster
from tools.audit_lokkestiiz_strategy_timeline import (
    _events,
    _metadata,
    _observed_primary_target,
    _start_ms,
)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _range_text(values: list[float], *, decimals: int = 2) -> str:
    if not values:
        return "n/a"
    return f"{min(values):,.{decimals}f}..{max(values):,.{decimals}f}"


def _pct(part: int, whole: int) -> float:
    return (part / whole * 100.0) if whole else 0.0


def _fight_observations(
    *,
    report_code: str,
    fight_id: int,
    fight: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    metadata = _metadata(fight)
    if metadata.get("kill") is not True:
        return [], []

    events = _events(fight)
    roster = _role_roster(fight)
    players = set(roster)
    if not events or len(players) != 12:
        return [], [
            f"{report_code} fight={fight_id}: skipped successful fight with incomplete events/12-player roster"
        ]

    start_ms = _start_ms(metadata, events)
    primary_target, _primary_damage, _ranking = _observed_primary_target(events, players)
    if primary_target is None:
        return [], [f"{report_code} fight={fight_id}: no primary hostile target resolved"]

    boundary_result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        events,
        boss_actor_id=primary_target,
        fight_start_time_ms=start_ms,
        evidence_source=f"ESO Logs {report_code} fight {fight_id}",
    )
    window_result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code=report_code,
        fight_id=fight_id,
        boundaries=boundary_result.boundaries,
    )

    unresolved = [*boundary_result.unresolved, *window_result.unresolved]
    observations: list[dict[str, Any]] = []
    for window in window_result.windows:
        try:
            occurrence = int(window.semantic_key.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            continue
        summary = _summarize_window(
            events,
            start_ms=start_ms,
            start_s=window.start_seconds,
            end_s=window.end_seconds,
            primary_target=primary_target,
            roster=roster,
        )
        duration = float(summary["duration"])
        incoming = summary["incoming_by_role"]
        observations.append(
            {
                "report": report_code,
                "fight_id": fight_id,
                "occurrence": occurrence,
                "start": float(window.start_seconds),
                "end": float(window.end_seconds),
                "duration": duration,
                "tank_inc_ps": float(incoming.get("Tank", 0.0)) / duration,
                "healer_inc_ps": float(incoming.get("Healer", 0.0)) / duration,
                "dps_inc_ps": float(incoming.get("DPS", 0.0)) / duration,
                "healer_output_ps": float(summary["healer_output"]) / duration,
                "other_hostile_dps": float(summary["other_enemy_damage"]) / duration,
                "deaths": len(summary["deaths"]),
                "resurrects": len(summary["resurrects"]),
                "interrupts": int(sum(summary["interrupts"].values())),
            }
        )
    return observations, unresolved


def build_report(payload: dict[str, Any]) -> str:
    all_rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    successful_fights = 0

    for report_code, fight_id_text, fight in _fight_rows(payload):
        metadata = _metadata(fight)
        if metadata.get("kill") is not True:
            continue
        successful_fights += 1
        rows, issues = _fight_observations(
            report_code=report_code,
            fight_id=int(fight_id_text),
            fight=fight,
        )
        all_rows.extend(rows)
        unresolved.extend(issues)

    by_flight: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        by_flight[int(row["occurrence"])].append(row)

    lines: list[str] = []
    lines.append("LOKKESTIIZ SUCCESSFUL-KILL FLIGHT CORPUS COMPARISON")
    lines.append("=" * 58)
    lines.append(f"Successful kills found: {successful_fights}")
    lines.append(f"Reviewed flight windows resolved: {len(all_rows)}")
    lines.append("")

    for occurrence in (1, 2, 3):
        rows = by_flight.get(occurrence, [])
        lines.append(f"FLIGHT {occurrence}")
        lines.append("-" * 58)
        lines.append(f"kills represented: {len(rows)}/{successful_fights}")
        if not rows:
            lines.append("No reviewed observations resolved.")
            lines.append("")
            continue

        durations = [float(row["duration"]) for row in rows]
        starts = [float(row["start"]) for row in rows]
        tank = [float(row["tank_inc_ps"]) for row in rows]
        healer = [float(row["healer_inc_ps"]) for row in rows]
        dps = [float(row["dps_inc_ps"]) for row in rows]
        healer_output = [float(row["healer_output_ps"]) for row in rows]
        add_dps = [float(row["other_hostile_dps"]) for row in rows]
        death_windows = sum(1 for row in rows if int(row["deaths"]) > 0)
        interrupt_windows = sum(1 for row in rows if int(row["interrupts"]) > 0)

        lines.append(
            f"duration: mean={_mean(durations):.2f}s | median={_median(durations):.2f}s | "
            f"range={_range_text(durations)}s"
        )
        lines.append(
            f"observed start clock: mean={_mean(starts):.2f}s | median={_median(starts):.2f}s | "
            f"range={_range_text(starts)}s"
        )
        lines.append(
            "incoming pressure mean (range): "
            f"tank={_mean(tank):,.0f}/s ({_range_text(tank, decimals=0)}) | "
            f"healer={_mean(healer):,.0f}/s ({_range_text(healer, decimals=0)}) | "
            f"dps={_mean(dps):,.0f}/s ({_range_text(dps, decimals=0)})"
        )
        lines.append(
            f"healer output: mean={_mean(healer_output):,.0f}/s | range={_range_text(healer_output, decimals=0)}"
        )
        lines.append(
            f"non-boss hostile damage: mean={_mean(add_dps):,.0f}/s | range={_range_text(add_dps, decimals=0)}"
        )
        lines.append(
            f"windows with player death(s): {death_windows}/{len(rows)} ({_pct(death_windows, len(rows)):.1f}%)"
        )
        lines.append(
            f"windows with interrupt(s): {interrupt_windows}/{len(rows)} ({_pct(interrupt_windows, len(rows)):.1f}%)"
        )
        lines.append("")

    complete_kills = 0
    rows_by_fight: dict[tuple[str, int], dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in all_rows:
        key = (str(row["report"]), int(row["fight_id"]))
        rows_by_fight[key][int(row["occurrence"])] = row

    highest_pressure_counts: dict[int, int] = defaultdict(int)
    highest_healer_output_counts: dict[int, int] = defaultdict(int)
    for flights in rows_by_fight.values():
        if set(flights) != {1, 2, 3}:
            continue
        complete_kills += 1
        pressure_winner = max(
            flights,
            key=lambda occ: (
                float(flights[occ]["tank_inc_ps"])
                + float(flights[occ]["healer_inc_ps"])
                + float(flights[occ]["dps_inc_ps"])
            ),
        )
        healer_output_winner = max(
            flights,
            key=lambda occ: float(flights[occ]["healer_output_ps"]),
        )
        highest_pressure_counts[pressure_winner] += 1
        highest_healer_output_counts[healer_output_winner] += 1

    lines.append("WITHIN-KILL RELATIVE PATTERN")
    lines.append("-" * 58)
    lines.append(f"complete 3-flight kills compared: {complete_kills}")
    for occurrence in (1, 2, 3):
        lines.append(
            f"flight {occurrence}: highest combined incoming pressure in "
            f"{highest_pressure_counts.get(occurrence, 0)}/{complete_kills}; "
            f"highest healer output in {highest_healer_output_counts.get(occurrence, 0)}/{complete_kills}"
        )

    if unresolved:
        lines.append("")
        lines.append("UNRESOLVED / SKIPPED")
        lines.append("-" * 58)
        lines.extend(str(row) for row in unresolved)

    lines.append("")
    lines.append("NOTE: these are distributions of observed successful clears, not universal fixed")
    lines.append("timings or canonical pressure values. Use recurrence across clears as strategy evidence.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare reviewed Lokkestiiz flight observations across successful corpus kills."
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}")
        return 2

    with args.path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        print("Expected a JSON object at the top level.")
        return 2

    print(build_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
