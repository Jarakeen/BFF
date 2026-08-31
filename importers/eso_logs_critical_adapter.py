from __future__ import annotations

"""Normalize ESO Logs damage/heal events into positive crit observations.

ESO Logs raw damage/heal events expose ``isCritical`` and ``isTick``.  This
adapter extracts only positive critical observations and converts them into the
source-agnostic records consumed by ``skill_critical_observation_importer``.

Important safety rules:
- non-critical events are ignored, never converted into ``can_crit = False``;
- ability names are never used as identifiers;
- events without a numeric ability id or recognizable damage/heal family are
  skipped and reported;
- output is normalized JSON/JSONL only; this adapter does not modify ``eso.db``.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_critical_observation import CriticalEventFamily, RuntimeCriticalObservation


_DAMAGE_EVENT_TYPES = {
    "damage",
    "damagedone",
    "damagetaken",
}
_HEAL_EVENT_TYPES = {
    "heal",
    "healing",
    "healdone",
}


@dataclass(frozen=True)
class EsoLogsCriticalAdapterSummary:
    events_scanned: int
    critical_events: int
    normalized_groups: int
    normalized_critical_events: int
    skipped_noncritical: int
    skipped_missing_ability_id: int
    skipped_unknown_event_type: int


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no", "", "none", "null"}:
        return False
    return False


def _ability_id(event: dict[str, Any]) -> int | None:
    for key in ("abilityGameID", "abilityID", "abilityId", "ability_id"):
        value = event.get(key)
        if value is None:
            continue
        try:
            ability_id = int(value)
        except (TypeError, ValueError):
            continue
        if ability_id > 0:
            return ability_id

    ability = event.get("ability")
    if isinstance(ability, dict):
        for key in ("gameID", "gameId", "guid", "id"):
            value = ability.get(key)
            if value is None:
                continue
            try:
                ability_id = int(value)
            except (TypeError, ValueError):
                continue
            if ability_id > 0:
                return ability_id

    return None


def _event_family(event: dict[str, Any]) -> CriticalEventFamily | None:
    raw_type = str(
        event.get("type")
        or event.get("eventType")
        or event.get("dataType")
        or event.get("kind")
        or ""
    ).strip().casefold().replace("_", "").replace(" ", "")

    is_tick = _as_bool(event.get("isTick", event.get("is_tick", False)))

    if raw_type in _DAMAGE_EVENT_TYPES:
        return (
            CriticalEventFamily.DAMAGE_PERIODIC
            if is_tick
            else CriticalEventFamily.DAMAGE_DIRECT
        )
    if raw_type in _HEAL_EVENT_TYPES:
        return (
            CriticalEventFamily.HEAL_PERIODIC
            if is_tick
            else CriticalEventFamily.HEAL_DIRECT
        )
    return None


def _looks_like_event(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "isCritical",
            "isTick",
            "abilityGameID",
            "abilityID",
            "abilityId",
            "ability",
        )
    ) and any(key in value for key in ("type", "eventType", "dataType", "kind"))


def _walk_events(value: Any) -> Iterable[dict[str, Any]]:
    """Yield event-like objects from raw arrays or nested GraphQL/report wrappers."""

    if isinstance(value, list):
        for item in value:
            yield from _walk_events(item)
        return

    if not isinstance(value, dict):
        return

    if _looks_like_event(value):
        yield value
        return

    # Prefer conventional event containers first, then recurse through any other
    # nested dict/list values so GraphQL wrappers remain supported without a
    # hardcoded response path.
    prioritized = []
    remainder = []
    for key, child in value.items():
        if not isinstance(child, (dict, list)):
            continue
        if str(key).casefold() in {"events", "data", "entries", "results"}:
            prioritized.append(child)
        else:
            remainder.append(child)

    for child in (*prioritized, *remainder):
        yield from _walk_events(child)


def load_eso_logs_events(path: str | Path) -> tuple[dict[str, Any], ...]:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    text = source_path.read_text(encoding="utf-8").strip()
    if not text:
        return ()

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        return tuple(event for record in records for event in _walk_events(record))

    return tuple(_walk_events(decoded))


def normalize_eso_logs_critical_events(
    events: tuple[dict[str, Any], ...],
    *,
    source: str,
) -> tuple[tuple[RuntimeCriticalObservation, ...], EsoLogsCriticalAdapterSummary]:
    source_text = str(source or "").strip()
    if not source_text:
        raise ValueError("source is required")

    grouped: Counter[tuple[int, CriticalEventFamily]] = Counter()
    skipped_noncritical = 0
    skipped_missing_ability_id = 0
    skipped_unknown_event_type = 0
    critical_events = 0

    for event in events:
        if not _as_bool(event.get("isCritical", event.get("is_critical", False))):
            skipped_noncritical += 1
            continue

        critical_events += 1
        ability_id = _ability_id(event)
        if ability_id is None:
            skipped_missing_ability_id += 1
            continue

        family = _event_family(event)
        if family is None:
            skipped_unknown_event_type += 1
            continue

        grouped[(ability_id, family)] += 1

    observations = tuple(
        RuntimeCriticalObservation(
            ability_id=ability_id,
            event_family=family,
            source=source_text,
            observed_count=count,
        )
        for (ability_id, family), count in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1].value)
        )
    )

    return observations, EsoLogsCriticalAdapterSummary(
        events_scanned=len(events),
        critical_events=critical_events,
        normalized_groups=len(observations),
        normalized_critical_events=sum(item.observed_count for item in observations),
        skipped_noncritical=skipped_noncritical,
        skipped_missing_ability_id=skipped_missing_ability_id,
        skipped_unknown_event_type=skipped_unknown_event_type,
    )


def write_normalized_observations(
    path: str | Path,
    observations: tuple[RuntimeCriticalObservation, ...],
    *,
    jsonl: bool = False,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    records = [
        {
            "ability_id": item.ability_id,
            "event_family": item.event_family.value,
            "source": item.source,
            "observed_count": item.observed_count,
        }
        for item in observations
    ]

    if jsonl:
        target.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
    else:
        target.write_text(
            json.dumps(records, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert ESO Logs damage/heal event JSON into normalized positive "
            "critical-observation records. Does not modify the ESO database."
        )
    )
    parser.add_argument("events", help="ESO Logs event JSON/JSONL file")
    parser.add_argument(
        "--source",
        required=True,
        help="Provenance label, e.g. 'ESO Logs report ABC123 fight 7'",
    )
    parser.add_argument("--output", help="Optional normalized JSON/JSONL output file")
    parser.add_argument("--jsonl", action="store_true", help="Write normalized output as JSONL")
    args = parser.parse_args()

    events = load_eso_logs_events(args.events)
    observations, summary = normalize_eso_logs_critical_events(events, source=args.source)

    if args.output:
        write_normalized_observations(args.output, observations, jsonl=args.jsonl)

    print("\n========================================")
    print(" PHASE 3 ESO LOGS CRIT ADAPTER")
    print("========================================")
    print(f"Input:                         {args.events}")
    print(f"Source:                        {args.source}")
    print(f"Events scanned:                {summary.events_scanned}")
    print(f"Critical events seen:          {summary.critical_events}")
    print(f"Normalized observation groups: {summary.normalized_groups}")
    print(f"Normalized critical events:    {summary.normalized_critical_events}")
    print(f"Non-critical events ignored:   {summary.skipped_noncritical}")
    print(f"Missing ability id skipped:    {summary.skipped_missing_ability_id}")
    print(f"Unknown event type skipped:    {summary.skipped_unknown_event_type}")
    print("Negative inference:            disabled")
    if args.output:
        print(f"Output:                        {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
