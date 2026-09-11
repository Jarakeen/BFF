from __future__ import annotations

"""Read-only single-fight timeline audit for the local Lokkestiiz ESO Logs corpus.

This is observational research tooling only. It does not write to eso.db, promote
mechanics, or treat one logged group's behavior as canonical encounter truth.

The audit identifies the hostile target that received the most friendly-player
damage as the *observed primary boss target* for the selected fight. It then bins
the fight into short windows and reports boss-target damage, damage to other
hostile targets, incoming player damage, healer output, player deaths, and
interrupts. This is useful for spotting candidate boss-unavailable/add-active
windows and raid-pressure spikes before human mechanic review.

Examples:

    python tools/audit_lokkestiiz_strategy_timeline.py \
        --report btZpy9j6KzYXkRL3 --fight-id 6

    python tools/audit_lokkestiiz_strategy_timeline.py \
        --report btZpy9j6KzYXkRL3 --fight-id 6 --bin-seconds 5
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from tools.audit_lokkestiiz_strategy_corpus import (
    DEFAULT_PATH,
    _ability_name,
    _amount,
    _format_duration,
    _int_or_none,
    _number,
    _role_roster,
)


def _selected_fight(
    payload: dict[str, Any],
    *,
    report_code: str,
    fight_id: int,
) -> dict[str, Any]:
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError("expected top-level 'reports' object")
    report = reports.get(report_code)
    if not isinstance(report, dict):
        raise KeyError(f"report {report_code!r} not found in corpus")
    fights = report.get("fights")
    if not isinstance(fights, dict):
        raise KeyError(f"report {report_code!r} has no fights object")
    fight = fights.get(str(fight_id))
    if not isinstance(fight, dict):
        raise KeyError(f"fight {fight_id} not found in report {report_code}")
    return fight


def _events(fight: dict[str, Any]) -> list[dict[str, Any]]:
    value = fight.get("events")
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _metadata(fight: dict[str, Any]) -> dict[str, Any]:
    value = fight.get("metadata")
    return value if isinstance(value, dict) else {}


def _start_ms(metadata: dict[str, Any], events: list[dict[str, Any]]) -> float:
    start = _number(metadata.get("startTime"))
    if start is not None:
        return start
    timestamps = [_number(row.get("timestamp")) for row in events]
    resolved = [value for value in timestamps if value is not None]
    return min(resolved) if resolved else 0.0


def _end_ms(metadata: dict[str, Any], events: list[dict[str, Any]]) -> float:
    end = _number(metadata.get("endTime"))
    if end is not None:
        return end
    timestamps = [_number(row.get("timestamp")) for row in events]
    resolved = [value for value in timestamps if value is not None]
    return max(resolved) if resolved else 0.0


def _player_ids(roster: dict[int, tuple[str, str, str]]) -> set[int]:
    return set(roster)


def _healer_ids(roster: dict[int, tuple[str, str, str]]) -> set[int]:
    return {
        actor_id
        for actor_id, (role, _name, _class_name) in roster.items()
        if role == "Healer"
    }


def _role_for_target(
    target_id: int | None,
    roster: dict[int, tuple[str, str, str]],
) -> str | None:
    if target_id is None:
        return None
    row = roster.get(target_id)
    return row[0] if row else None


def _observed_primary_target(
    events: list[dict[str, Any]],
    player_ids: set[int],
) -> tuple[int | None, float, tuple[tuple[int, float], ...]]:
    by_target: dict[int, float] = defaultdict(float)
    for event in events:
        if str(event.get("type") or "").casefold() != "damage":
            continue
        source_id = _int_or_none(event.get("sourceID"))
        target_id = _int_or_none(event.get("targetID"))
        if source_id not in player_ids or target_id is None:
            continue
        if event.get("targetIsFriendly") is True:
            continue
        by_target[target_id] += _amount(event)

    ranked = tuple(sorted(by_target.items(), key=lambda row: (-row[1], row[0])))
    if not ranked:
        return None, 0.0, ()
    return ranked[0][0], ranked[0][1], ranked[:10]


def _bin_index(timestamp_ms: float, start_ms: float, bin_seconds: float) -> int:
    return max(0, int(((timestamp_ms - start_ms) / 1000.0) // bin_seconds))


def _fmt_rate(value: float, seconds: float) -> str:
    return f"{(value / seconds):,.0f}"


def _ability_label(event: dict[str, Any], *, killing: bool = False) -> str:
    if killing:
        ability_id = _int_or_none(event.get("killingAbilityGameID"))
        return str(ability_id) if ability_id is not None else "unknown"
    name = _ability_name(event)
    ability_id = _int_or_none(event.get("abilityGameID"))
    if name and ability_id is not None:
        return f"{name} [{ability_id}]"
    if name:
        return name
    return str(ability_id) if ability_id is not None else "unknown"


def build_timeline(
    payload: dict[str, Any],
    *,
    report_code: str,
    fight_id: int,
    bin_seconds: float,
    top_hostile_abilities: int,
) -> str:
    fight = _selected_fight(payload, report_code=report_code, fight_id=fight_id)
    metadata = _metadata(fight)
    events = _events(fight)
    roster = _role_roster(fight)
    players = _player_ids(roster)
    healers = _healer_ids(roster)

    start_ms = _start_ms(metadata, events)
    end_ms = _end_ms(metadata, events)
    duration_seconds = max(0.0, (end_ms - start_ms) / 1000.0)

    primary_target, primary_damage, target_ranking = _observed_primary_target(events, players)
    all_player_enemy_damage = sum(value for _target, value in target_ranking)

    bins: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "boss_damage": 0.0,
            "other_enemy_damage": 0.0,
            "incoming_damage": 0.0,
            "healer_output": 0.0,
            "deaths": [],
            "interrupts": 0,
        }
    )

    hostile_damage_by_ability: Counter[int] = Counter()
    hostile_casts: Counter[int] = Counter()
    interrupt_abilities: Counter[tuple[int | None, int | None]] = Counter()
    death_rows: list[tuple[float, str, str, int | None]] = []

    for event in events:
        timestamp = _number(event.get("timestamp"))
        if timestamp is None:
            continue
        index = _bin_index(timestamp, start_ms, bin_seconds)
        bucket = bins[index]
        event_type = str(event.get("type") or "").casefold()
        source_id = _int_or_none(event.get("sourceID"))
        target_id = _int_or_none(event.get("targetID"))

        if event_type == "damage":
            amount = _amount(event)
            if source_id in players and event.get("targetIsFriendly") is not True:
                if primary_target is not None and target_id == primary_target:
                    bucket["boss_damage"] += amount
                else:
                    bucket["other_enemy_damage"] += amount

            if target_id in players and event.get("sourceIsFriendly") is not True:
                bucket["incoming_damage"] += amount
                ability_id = _int_or_none(event.get("abilityGameID"))
                if ability_id is not None:
                    hostile_damage_by_ability[ability_id] += int(amount)

        elif event_type == "heal" and source_id in healers:
            bucket["healer_output"] += _amount(event)

        elif event_type == "death" and target_id in players:
            role = _role_for_target(target_id, roster) or "Unknown"
            actor = roster.get(target_id)
            name = actor[1] if actor else f"actor {target_id}"
            rel = max(0.0, (timestamp - start_ms) / 1000.0)
            killing_id = _int_or_none(event.get("killingAbilityGameID"))
            bucket["deaths"].append((role, name, killing_id))
            death_rows.append((rel, role, name, killing_id))

        elif event_type == "interrupt":
            if source_id in players or target_id in players:
                bucket["interrupts"] += 1
                interrupt_abilities[
                    (
                        _int_or_none(event.get("abilityGameID")),
                        _int_or_none(event.get("extraAbilityGameID")),
                    )
                ] += 1

        if event_type in {"begincast", "cast"} and event.get("sourceIsFriendly") is not True:
            ability_id = _int_or_none(event.get("abilityGameID"))
            if ability_id is not None:
                hostile_casts[ability_id] += 1

    lines: list[str] = []
    lines.append("LOKKESTIIZ STRATEGY TIMELINE AUDIT")
    lines.append("=" * 42)
    lines.append(f"Report: {report_code}")
    lines.append(f"Fight: {fight_id}")
    lines.append(f"Kill: {metadata.get('kill')}")
    lines.append(f"Difficulty: {metadata.get('difficulty')}")
    lines.append(f"Duration: {_format_duration(duration_seconds)}")
    lines.append(f"Events: {len(events):,}")
    lines.append(f"Resolved players: {len(players)}")
    lines.append("")

    lines.append("OBSERVED HOSTILE TARGET RANKING BY FRIENDLY DAMAGE")
    lines.append("-" * 42)
    total_enemy_damage = sum(value for _target, value in target_ranking)
    for target_id, damage in target_ranking:
        share = (damage / total_enemy_damage * 100.0) if total_enemy_damage else 0.0
        marker = " <- primary target" if target_id == primary_target else ""
        lines.append(f"target={target_id:<8} damage={damage:>14,.0f} share={share:6.2f}%{marker}")
    if primary_target is None:
        lines.append("No hostile target could be resolved from friendly damage events.")

    lines.append("")
    lines.append(f"TIMELINE ({bin_seconds:g}-SECOND WINDOWS)")
    lines.append("-" * 42)
    lines.append("window       bossDPS    otherDPS    raidIncPS    healerHPS  deaths  ints  observation")

    bin_count = int(duration_seconds // bin_seconds) + 1 if duration_seconds else 0
    for index in range(bin_count):
        bucket = bins[index]
        start_s = index * bin_seconds
        end_s = min(duration_seconds, start_s + bin_seconds)
        actual_seconds = max(0.001, end_s - start_s)
        boss_damage = float(bucket["boss_damage"])
        other_damage = float(bucket["other_enemy_damage"])
        incoming = float(bucket["incoming_damage"])
        healer_output = float(bucket["healer_output"])
        death_count = len(bucket["deaths"])
        interrupts = int(bucket["interrupts"])

        observation = ""
        if primary_target is not None and boss_damage <= 0.0 and other_damage > 0.0:
            observation = "no primary-target damage; other hostile damage active"
        elif primary_target is not None and boss_damage <= 0.0 and incoming > 0.0:
            observation = "no primary-target damage; raid still taking damage"
        if death_count:
            death_text = ", ".join(
                f"{role}:{name}" for role, name, _ability in bucket["deaths"]
            )
            observation = f"{observation}; " if observation else ""
            observation += f"deaths={death_text}"

        lines.append(
            f"{start_s:5.0f}-{end_s:<5.0f} "
            f"{_fmt_rate(boss_damage, actual_seconds):>10} "
            f"{_fmt_rate(other_damage, actual_seconds):>11} "
            f"{_fmt_rate(incoming, actual_seconds):>12} "
            f"{_fmt_rate(healer_output, actual_seconds):>11} "
            f"{death_count:>6} {interrupts:>5}  {observation}"
        )

    lines.append("")
    lines.append(f"TOP {top_hostile_abilities} HOSTILE DAMAGE ABILITY IDS AGAINST PLAYERS")
    lines.append("-" * 42)
    for ability_id, damage in hostile_damage_by_ability.most_common(top_hostile_abilities):
        lines.append(f"{ability_id:>9}  damage={damage:>14,}")

    lines.append("")
    lines.append(f"TOP {top_hostile_abilities} HOSTILE CAST / BEGINCAST ABILITY IDS")
    lines.append("-" * 42)
    for ability_id, count in hostile_casts.most_common(top_hostile_abilities):
        lines.append(f"{ability_id:>9}  casts={count:>6,}")

    lines.append("")
    lines.append("PLAYER DEATH TIMELINE")
    lines.append("-" * 42)
    if death_rows:
        for rel, role, name, killing_id in death_rows:
            lines.append(
                f"t={rel:7.2f}s | {role:6} | {name} | killingAbilityGameID={killing_id}"
            )
    else:
        lines.append("No player deaths observed.")

    lines.append("")
    lines.append("INTERRUPT EVENT PAIRS (abilityGameID -> extraAbilityGameID)")
    lines.append("-" * 42)
    if interrupt_abilities:
        for (ability_id, extra_id), count in interrupt_abilities.most_common():
            lines.append(f"{ability_id} -> {extra_id} | {count}")
    else:
        lines.append("No player-related interrupt events observed.")

    lines.append("")
    lines.append("NOTE: the 'primary target' is inferred only as the hostile target receiving the")
    lines.append("most friendly-player damage in this logged fight. Timeline observations are")
    lines.append("runtime evidence candidates, not canonical mechanic claims.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one Lokkestiiz corpus fight as a strategy-oriented timeline."
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--report", required=True)
    parser.add_argument("--fight-id", type=int, required=True)
    parser.add_argument("--bin-seconds", type=float, default=10.0)
    parser.add_argument("--top-hostile-abilities", type=int, default=20)
    args = parser.parse_args()

    if args.bin_seconds <= 0:
        print("--bin-seconds must be greater than zero")
        return 2
    if not args.path.exists():
        print(f"File not found: {args.path}")
        return 2

    with args.path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        print("Expected a JSON object at the top level.")
        return 2

    try:
        output = build_timeline(
            payload,
            report_code=args.report,
            fight_id=args.fight_id,
            bin_seconds=args.bin_seconds,
            top_hostile_abilities=args.top_hostile_abilities,
        )
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
