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
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PATH = Path("research/raw/lokkestiiz_corpus.json")


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


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
    lines.append("NOTE: this output is observational only. It does not promote timing, ability IDs,")
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
