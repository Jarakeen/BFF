from __future__ import annotations

"""Read-only strategy summary for reviewed Lokkestiiz flight windows.

The raw ESO Logs corpus remains local under research/raw. This tool reuses the
existing reviewed flight-boundary and semantic window services, then aggregates
observed role pressure and hostile-target activity inside each flight. It does
not write canonical encounter data.
"""

import argparse
from collections import Counter, defaultdict
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
from services.performance_raid_review_lokkestiiz_window_service import (
    PerformanceRaidReviewLokkestiizWindowService,
)
from tools.audit_lokkestiiz_strategy_corpus import (
    DEFAULT_PATH,
    _amount,
    _int_or_none,
    _number,
    _role_roster,
)
from tools.audit_lokkestiiz_strategy_timeline import (
    _events,
    _metadata,
    _observed_primary_target,
    _selected_fight,
    _start_ms,
)


def _fmt_seconds(value: float) -> str:
    minutes, seconds = divmod(float(value), 60.0)
    return f"{int(minutes)}:{seconds:05.2f}"


def _player_ids_by_role(
    roster: dict[int, tuple[str, str, str]],
) -> dict[str, set[int]]:
    result: dict[str, set[int]] = defaultdict(set)
    for actor_id, (role, _name, _class_name) in roster.items():
        result[role].add(actor_id)
    return result


def _in_window(timestamp_ms: float, *, start_ms: float, start_s: float, end_s: float) -> bool:
    rel = (timestamp_ms - start_ms) / 1000.0
    return start_s <= rel < end_s


def _summarize_window(
    events: list[dict[str, Any]],
    *,
    start_ms: float,
    start_s: float,
    end_s: float,
    primary_target: int,
    roster: dict[int, tuple[str, str, str]],
) -> dict[str, Any]:
    by_role = _player_ids_by_role(roster)
    all_players = set(roster)
    healer_ids = by_role.get("Healer", set())

    incoming_by_role: dict[str, float] = defaultdict(float)
    healer_output = 0.0
    other_enemy_damage = 0.0
    other_target_damage: dict[int, float] = defaultdict(float)
    boss_damage = 0.0
    deaths: list[tuple[float, str, str, int | None]] = []
    resurrects: list[tuple[float, str, str]] = []
    interrupts: Counter[tuple[int | None, int | None]] = Counter()

    for event in events:
        timestamp = _number(event.get("timestamp"))
        if timestamp is None or not _in_window(
            timestamp,
            start_ms=start_ms,
            start_s=start_s,
            end_s=end_s,
        ):
            continue

        event_type = str(event.get("type") or "").casefold()
        source_id = _int_or_none(event.get("sourceID"))
        target_id = _int_or_none(event.get("targetID"))
        rel = max(0.0, (timestamp - start_ms) / 1000.0)

        if event_type == "damage":
            amount = _amount(event)
            if source_id in all_players and event.get("targetIsFriendly") is not True:
                if target_id == primary_target:
                    boss_damage += amount
                elif target_id is not None:
                    other_enemy_damage += amount
                    other_target_damage[target_id] += amount

            if target_id in all_players and event.get("sourceIsFriendly") is not True:
                role = roster[target_id][0]
                incoming_by_role[role] += amount

        elif event_type == "heal" and source_id in healer_ids:
            healer_output += _amount(event)

        elif event_type == "death" and target_id in all_players:
            role, name, _class_name = roster[target_id]
            deaths.append(
                (
                    rel,
                    role,
                    name,
                    _int_or_none(event.get("killingAbilityGameID")),
                )
            )

        elif event_type == "resurrect" and target_id in all_players:
            role, name, _class_name = roster[target_id]
            resurrects.append((rel, role, name))

        elif event_type == "interrupt" and (source_id in all_players or target_id in all_players):
            interrupts[
                (
                    _int_or_none(event.get("abilityGameID")),
                    _int_or_none(event.get("extraAbilityGameID")),
                )
            ] += 1

    duration = max(0.001, end_s - start_s)
    return {
        "duration": duration,
        "boss_damage": boss_damage,
        "other_enemy_damage": other_enemy_damage,
        "other_target_damage": tuple(
            sorted(other_target_damage.items(), key=lambda row: (-row[1], row[0]))
        ),
        "incoming_by_role": dict(incoming_by_role),
        "healer_output": healer_output,
        "deaths": tuple(deaths),
        "resurrects": tuple(resurrects),
        "interrupts": interrupts,
    }


def build_report(
    payload: dict[str, Any],
    *,
    report_code: str,
    fight_id: int,
) -> str:
    fight = _selected_fight(payload, report_code=report_code, fight_id=fight_id)
    metadata = _metadata(fight)
    events = _events(fight)
    roster = _role_roster(fight)
    players = set(roster)
    start_ms = _start_ms(metadata, events)

    primary_target, primary_damage, _ranking = _observed_primary_target(events, players)
    if primary_target is None:
        raise ValueError("could not resolve observed primary hostile target")

    evidence_source = f"ESO Logs {report_code} fight {fight_id}"
    boundary_result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        events,
        boss_actor_id=primary_target,
        fight_start_time_ms=start_ms,
        evidence_source=evidence_source,
    )
    window_result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code=report_code,
        fight_id=fight_id,
        boundaries=boundary_result.boundaries,
    )

    lines: list[str] = []
    lines.append("LOKKESTIIZ FLIGHT STRATEGY-WINDOW AUDIT")
    lines.append("=" * 45)
    lines.append(f"Report: {report_code}")
    lines.append(f"Fight: {fight_id}")
    lines.append(f"Kill: {metadata.get('kill')}")
    lines.append(f"Difficulty: {metadata.get('difficulty')}")
    lines.append(f"Resolved players: {len(players)}")
    lines.append(f"Observed primary hostile target: {primary_target}")
    lines.append(f"Observed primary-target damage: {primary_damage:,.0f}")
    lines.append("")

    if boundary_result.unresolved or window_result.unresolved:
        lines.append("UNRESOLVED")
        lines.append("-" * 45)
        for row in (*boundary_result.unresolved, *window_result.unresolved):
            lines.append(str(row))
        lines.append("")

    lines.append("REVIEWED FLIGHT WINDOWS")
    lines.append("-" * 45)
    for window in window_result.windows:
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
        lines.append(
            f"{window.label} | {_fmt_seconds(window.start_seconds)} -> {_fmt_seconds(window.end_seconds)} "
            f"| duration={duration:.2f}s"
        )
        lines.append(
            "  pressure: "
            f"tank={incoming.get('Tank', 0.0) / duration:,.0f}/s | "
            f"healer={incoming.get('Healer', 0.0) / duration:,.0f}/s | "
            f"dps={incoming.get('DPS', 0.0) / duration:,.0f}/s | "
            f"healer_output={float(summary['healer_output']) / duration:,.0f}/s"
        )
        lines.append(
            "  damage targets: "
            f"boss={float(summary['boss_damage']):,.0f} | "
            f"other_hostiles={float(summary['other_enemy_damage']):,.0f}"
        )
        target_rows = summary["other_target_damage"]
        if target_rows:
            rendered = ", ".join(
                f"{target_id}={damage:,.0f}"
                for target_id, damage in target_rows[:8]
            )
            lines.append(f"  observed non-boss targets: {rendered}")
        else:
            lines.append("  observed non-boss targets: none")

        deaths = summary["deaths"]
        resurrects = summary["resurrects"]
        interrupts = summary["interrupts"]
        lines.append(
            f"  recovery/events: deaths={len(deaths)} | resurrects={len(resurrects)} | "
            f"interrupts={sum(interrupts.values())}"
        )
        for rel, role, name, killing_id in deaths:
            lines.append(
                f"    death t={rel:.2f}s | {role} | {name} | killingAbilityGameID={killing_id}"
            )
        for rel, role, name in resurrects:
            lines.append(f"    resurrect t={rel:.2f}s | {role} | {name}")
        if interrupts:
            rendered = ", ".join(
                f"{ability_id}->{extra_id} x{count}"
                for (ability_id, extra_id), count in interrupts.most_common()
            )
            lines.append(f"    interrupt pairs: {rendered}")
        lines.append("")

    lines.append("NOTE: all values above are observed runtime evidence for this logged fight.")
    lines.append("Raw actor and ability IDs remain evidence signatures, not canonical semantic identity.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize role pressure and add activity inside reviewed Lokke flight windows."
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
        print(build_report(payload, report_code=args.report, fight_id=args.fight_id))
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
