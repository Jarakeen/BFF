from __future__ import annotations

"""Read-only exploratory summary for the local Lokkestiiz ESO Logs corpus.

The raw corpus is intentionally kept under ``research/raw`` and out of GitHub.
This tool does not write canonical encounter data or infer game mechanics. It only
summarizes the observational material already present in the local corpus so a
human can decide what is worth reviewing for Encounter strategy guides.

Usage:

    python tools/audit_lokkestiiz_strategy_corpus.py
    python tools/audit_lokkestiiz_strategy_corpus.py --path research/raw/lokkestiiz_corpus.json
    python tools/audit_lokkestiiz_strategy_corpus.py --top-abilities 30
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PATH = Path("research/raw/lokkestiiz_corpus.json")
_ROLE_KEYS = (("tanks", "Tank"), ("healers", "Healer"), ("dps", "DPS"))


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _int_or_none(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _duration_seconds(metadata: dict[str, Any]) -> float | None:
    start = _number(metadata.get("startTime"))
    end = _number(metadata.get("endTime"))
    if start is None or end is None or end < start:
        return None
    return (end - start) / 1000.0


def _ability_name(event: dict[str, Any]) -> str | None:
    ability = event.get("ability")
    if isinstance(ability, dict):
        name = ability.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    name = event.get("abilityName")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _fight_rows(payload: dict[str, Any]) -> Iterable[tuple[str, str, dict[str, Any]]]:
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError("expected top-level 'reports' object in Lokkestiiz corpus")

    for report_code, report in reports.items():
        if not isinstance(report, dict):
            continue
        fights = report.get("fights")
        if not isinstance(fights, dict):
            continue
        for fight_id, fight in fights.items():
            if isinstance(fight, dict):
                yield str(report_code), str(fight_id), fight


def _event_field_counts(events: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for event in events:
        counts.update(str(key) for key in event.keys())
    return counts


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    minutes, remainder = divmod(seconds, 60.0)
    return f"{int(minutes)}:{remainder:04.1f}"


def _fight_label(metadata: dict[str, Any]) -> str:
    name = metadata.get("name")
    return str(name) if name else "Lokkestiiz"


def _normalize_player_details(value: Any) -> dict[str, Any]:
    """Accept the direct or lightly wrapped playerDetails shapes seen in ESO Logs."""
    current = value
    for key in ("data", "playerDetails"):
        if isinstance(current, dict) and key in current and isinstance(current[key], dict):
            current = current[key]
    return current if isinstance(current, dict) else {}


def _role_roster(fight: dict[str, Any]) -> dict[int, tuple[str, str, str]]:
    details = _normalize_player_details(fight.get("player_details"))
    roster: dict[int, tuple[str, str, str]] = {}
    for key, role in _ROLE_KEYS:
        actors = details.get(key)
        if not isinstance(actors, list):
            continue
        for actor in actors:
            if not isinstance(actor, dict):
                continue
            actor_id = _int_or_none(actor.get("id"))
            if actor_id is None:
                continue
            name = str(actor.get("name") or f"Anonymous {actor_id}").strip()
            class_name = str(actor.get("type") or actor.get("class") or "").strip()
            roster[actor_id] = (role, name, class_name)
    return roster


def _amount(event: dict[str, Any]) -> float:
    value = _number(event.get("amount"))
    return max(0.0, value or 0.0)


def _role_observations(
    events: list[dict[str, Any]],
    roster: dict[int, tuple[str, str, str]],
    *,
    top_abilities: int = 8,
) -> list[str]:
    actor_ids_by_role: dict[str, set[int]] = defaultdict(set)
    for actor_id, (role, _name, _class_name) in roster.items():
        actor_ids_by_role[role].add(actor_id)

    lines: list[str] = []
    for role in ("Tank", "Healer", "DPS"):
        actor_ids = actor_ids_by_role.get(role, set())
        if not actor_ids:
            lines.append(f"{role}: no actors resolved from player_details")
            continue

        outgoing_damage = 0.0
        outgoing_healing = 0.0
        incoming_damage = 0.0
        casts = 0
        deaths = 0
        resurrects = 0
        ability_counts: Counter[tuple[int | None, str | None]] = Counter()

        for event in events:
            event_type = str(event.get("type") or "").casefold()
            source_id = _int_or_none(event.get("sourceID"))
            target_id = _int_or_none(event.get("targetID"))

            if source_id in actor_ids:
                if event_type == "damage":
                    outgoing_damage += _amount(event)
                elif event_type == "heal":
                    outgoing_healing += _amount(event)
                elif event_type in {"begincast", "cast"}:
                    casts += 1

                ability_id = _int_or_none(event.get("abilityGameID"))
                ability_name = _ability_name(event)
                if ability_id is not None or ability_name is not None:
                    ability_counts[(ability_id, ability_name)] += 1

            if target_id in actor_ids:
                if event_type == "damage":
                    incoming_damage += _amount(event)
                elif event_type == "death":
                    deaths += 1
                elif event_type == "resurrect":
                    resurrects += 1

        lines.append(
            f"{role}: actors={len(actor_ids)} | incoming_damage={incoming_damage:,.0f} | "
            f"outgoing_damage={outgoing_damage:,.0f} | outgoing_healing={outgoing_healing:,.0f} | "
            f"casts={casts:,} | deaths={deaths} | resurrects={resurrects}"
        )
        if ability_counts:
            compact = "; ".join(
                f"{name or ability_id} ({count:,})"
                for (ability_id, name), count in ability_counts.most_common(top_abilities)
            )
            lines.append(f"  top observed source abilities: {compact}")
    return lines


def _roster_lines(roster: dict[int, tuple[str, str, str]]) -> list[str]:
    lines: list[str] = []
    for role in ("Tank", "DPS", "Healer"):
        actors = [
            (actor_id, name, class_name)
            for actor_id, (actor_role, name, class_name) in roster.items()
            if actor_role == role
        ]
        actors.sort(key=lambda row: row[0])
        if not actors:
            lines.append(f"{role}: <none resolved>")
            continue
        rendered = ", ".join(
            f"{name}{f' [{class_name}]' if class_name else ''} (id={actor_id})"
            for actor_id, name, class_name in actors
        )
        lines.append(f"{role}: {rendered}")
    return lines


def build_summary(payload: dict[str, Any], *, top_abilities: int) -> str:
    rows = tuple(_fight_rows(payload))
    lines: list[str] = []
    lines.append("LOKKESTIIZ STRATEGY CORPUS AUDIT")
    lines.append("=" * 36)
    lines.append(f"Reports: {len({report for report, _, _ in rows})}")
    lines.append(f"Fights: {len(rows)}")
    lines.append("")

    all_events: list[dict[str, Any]] = []
    duration_values: list[float] = []
    kills = 0
    wipes = 0

    for report_code, fight_id, fight in rows:
        metadata = fight.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        raw_events = fight.get("events")
        events = [event for event in raw_events if isinstance(event, dict)] if isinstance(raw_events, list) else []
        all_events.extend(events)

        duration = _duration_seconds(metadata)
        if duration is not None:
            duration_values.append(duration)

        kill = metadata.get("kill")
        if kill is True:
            kills += 1
        elif kill is False:
            wipes += 1

        declared = fight.get("event_count")
        boss_pct = metadata.get("bossPercentage")
        difficulty = metadata.get("difficulty")
        lines.append(
            f"{report_code} fight={fight_id} | {_fight_label(metadata)} | "
            f"kill={kill} | difficulty={difficulty} | duration={_format_duration(duration)} | "
            f"events={len(events):,} declared={declared} | bossPercentage={boss_pct}"
        )

        roster = _role_roster(fight)
        lines.append("  ROLE ROSTER")
        lines.extend(f"    {row}" for row in _roster_lines(roster))
        lines.append("  ROLE OBSERVATIONS")
        lines.extend(f"    {row}" for row in _role_observations(events, roster))

    lines.append("")
    lines.append("CORPUS TOTALS")
    lines.append("-" * 36)
    lines.append(f"Kills: {kills}")
    lines.append(f"Wipes: {wipes}")
    lines.append(f"Events: {len(all_events):,}")
    if duration_values:
        lines.append(f"Shortest fight: {_format_duration(min(duration_values))}")
        lines.append(f"Longest fight:  {_format_duration(max(duration_values))}")
        lines.append(
            f"Mean duration:  {_format_duration(sum(duration_values) / len(duration_values))}"
        )

    event_types = Counter(str(event.get("type") or "<missing>") for event in all_events)
    lines.append("")
    lines.append("EVENT TYPES")
    lines.append("-" * 36)
    for event_type, count in event_types.most_common():
        lines.append(f"{event_type:30} {count:,}")

    ability_counts: Counter[tuple[int | None, str | None]] = Counter()
    for event in all_events:
        raw_id = event.get("abilityGameID")
        ability_id = int(raw_id) if isinstance(raw_id, (int, float)) else None
        name = _ability_name(event)
        if ability_id is not None or name is not None:
            ability_counts[(ability_id, name)] += 1

    lines.append("")
    lines.append(f"TOP {top_abilities} OBSERVED ABILITIES")
    lines.append("-" * 36)
    for (ability_id, name), count in ability_counts.most_common(max(0, top_abilities)):
        lines.append(f"{str(ability_id):>9} | {str(name):45} | {count:,}")

    field_counts = _event_field_counts(all_events)
    lines.append("")
    lines.append("RAW EVENT FIELDS AVAILABLE")
    lines.append("-" * 36)
    for field, count in sorted(field_counts.items(), key=lambda row: (-row[1], row[0])):
        coverage = (count / len(all_events) * 100.0) if all_events else 0.0
        lines.append(f"{field:30} {count:>10,}  {coverage:6.2f}%")

    lines.append("")
    lines.append("STRATEGY-GUIDE CANDIDATE SIGNALS")
    lines.append("-" * 36)
    candidates = {
        "damage/healing pressure": {"damage", "heal", "absorbed"},
        "casts / interrupt candidates": {"begincast", "cast"},
        "buff/debuff timing": {"applybuff", "refreshbuff", "removebuff", "applydebuff", "refreshdebuff", "removedebuff"},
        "deaths / recovery": {"death", "resurrect"},
        "resources / sustain": {"resourcechange"},
    }
    observed_types = {str(key).casefold() for key in event_types}
    for label, wanted in candidates.items():
        present = sorted(wanted & observed_types)
        lines.append(f"{label:30} {'available' if present else 'not seen'}" + (f" ({', '.join(present)})" if present else ""))

    lines.append("")
    lines.append("NOTE: role labels come from ESO Logs player_details for each fight.")
    lines.append("This output is observational only. It does not promote timing, ability IDs,")
    lines.append("or player behavior into canonical mechanics. Human review remains required.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize local Lokkestiiz ESO Logs corpus for strategy-guide research.")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--top-abilities", type=int, default=40)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}")
        return 2

    with args.path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        print("Expected a JSON object at the top level.")
        return 2

    print(build_summary(payload, top_abilities=args.top_abilities))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
