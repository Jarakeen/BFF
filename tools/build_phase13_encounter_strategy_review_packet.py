from __future__ import annotations

"""Build a non-canonical strategy review packet from a raw ESO Logs encounter corpus.

This is the encounter-generic equivalent of the Lokkestiiz strategy research tools.
It summarizes observable fight/role pressure and hostile log signatures for human
review. Numeric ESO Logs ability ids remain observational aliases only. No mechanic
identity, timing rule, or strategy claim is promoted by this tool.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from tools.audit_phase13_encounter_ability_aliases import discover_hostile_signatures


_ROLE_KEYS = (("tanks", "tank"), ("healers", "healer"), ("dps", "dps"))
_REVIEW_RULES = (
    "Numeric ESO Logs ability ids are observational aliases, not canonical mechanic identity.",
    "A repeated log signature is a review candidate, not a mechanic or strategy claim.",
    "Observed player behavior from one group is not universal encounter strategy.",
    "Canonical mechanic binding requires explicit human review with rationale.",
    "Runtime timing remains fight-local evidence unless repeated evidence is reviewed for promotion.",
)


def _int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _events(fight: dict[str, Any]) -> list[dict[str, Any]]:
    value = fight.get("events")
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _metadata(fight: dict[str, Any]) -> dict[str, Any]:
    value = fight.get("metadata")
    return value if isinstance(value, dict) else {}


def _normalize_player_details(value: object) -> dict[str, Any]:
    current = value
    for key in ("data", "playerDetails"):
        if isinstance(current, dict) and isinstance(current.get(key), dict):
            current = current[key]
    return current if isinstance(current, dict) else {}


def _roster(fight: dict[str, Any]) -> dict[int, str]:
    details = _normalize_player_details(fight.get("player_details"))
    result: dict[int, str] = {}
    for key, role in _ROLE_KEYS:
        rows = details.get(key)
        if isinstance(rows, dict):
            rows = list(rows.values())
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            actor_id = _int(row.get("id"))
            if actor_id is not None:
                result[actor_id] = role
    return result


def _fight_rows(payload: dict[str, Any]):
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError("expected top-level 'reports' object")
    for report_code, report in reports.items():
        if not isinstance(report, dict):
            continue
        fights = report.get("fights")
        if not isinstance(fights, dict):
            continue
        for fight_key, fight in fights.items():
            if isinstance(fight, dict):
                yield str(report_code), int(fight_key), fight


def _start_end(metadata: dict[str, Any], events: list[dict[str, Any]]) -> tuple[float, float]:
    timestamps = [
        value for row in events if (value := _number(row.get("timestamp"))) is not None
    ]
    start = _number(metadata.get("startTime"))
    end = _number(metadata.get("endTime"))
    if start is None:
        start = min(timestamps) if timestamps else 0.0
    if end is None:
        end = max(timestamps) if timestamps else start
    return float(start), max(float(start), float(end))


def _observed_primary_target(events: list[dict[str, Any]], players: set[int]) -> int | None:
    damage: dict[int, float] = defaultdict(float)
    for row in events:
        if str(row.get("type") or "").casefold() != "damage":
            continue
        source = _int(row.get("sourceID"))
        target = _int(row.get("targetID"))
        if source not in players or target is None or row.get("targetIsFriendly") is True:
            continue
        damage[target] += max(0.0, _number(row.get("amount")) or 0.0)
    return max(damage, key=damage.get) if damage else None


def _pressure_windows(
    fight: dict[str, Any],
    *,
    bin_seconds: float,
) -> list[dict[str, Any]]:
    events = _events(fight)
    metadata = _metadata(fight)
    roster = _roster(fight)
    players = set(roster)
    healers = {actor_id for actor_id, role in roster.items() if role == "healer"}
    primary = _observed_primary_target(events, players)
    start, end = _start_end(metadata, events)
    duration = max(0.0, (end - start) / 1000.0)
    bin_count = int(duration // bin_seconds) + 1 if duration else 0
    buckets = [
        {
            "index": index,
            "start_seconds": round(index * bin_seconds, 3),
            "end_seconds": round(min(duration, (index + 1) * bin_seconds), 3),
            "primary_target_damage": 0.0,
            "other_hostile_damage": 0.0,
            "incoming_player_damage": 0.0,
            "healer_output": 0.0,
            "deaths": 0,
            "interrupts": 0,
        }
        for index in range(bin_count)
    ]
    for row in events:
        timestamp = _number(row.get("timestamp"))
        if timestamp is None or not buckets:
            continue
        index = int(max(0.0, (timestamp - start) / 1000.0) // bin_seconds)
        if index >= len(buckets):
            index = len(buckets) - 1
        bucket = buckets[index]
        event_type = str(row.get("type") or "").casefold()
        source = _int(row.get("sourceID"))
        target = _int(row.get("targetID"))
        amount = max(0.0, _number(row.get("amount")) or 0.0)
        if event_type == "damage":
            if source in players and row.get("targetIsFriendly") is not True:
                key = "primary_target_damage" if primary is not None and target == primary else "other_hostile_damage"
                bucket[key] += amount
            if target in players and row.get("sourceIsFriendly") is not True:
                bucket["incoming_player_damage"] += amount
        elif event_type == "heal" and source in healers:
            bucket["healer_output"] += amount
        elif event_type == "death" and target in players:
            bucket["deaths"] += 1
        elif event_type == "interrupt" and (source in players or target in players):
            bucket["interrupts"] += 1

    for bucket in buckets:
        for key in (
            "primary_target_damage",
            "other_hostile_damage",
            "incoming_player_damage",
            "healer_output",
        ):
            bucket[key] = round(float(bucket[key]), 3)
    return buckets


def _candidate_families(path: Path, *, limit: int) -> list[dict[str, Any]]:
    signatures = discover_hostile_signatures(path=path)
    grouped: dict[int, dict[str, Any]] = {}
    for name, ability_id, raw_type, tick, count, fight_count in signatures:
        if ability_id is None:
            continue
        row = grouped.setdefault(
            int(ability_id),
            {
                "ability_game_id": int(ability_id),
                "observed_names": set(),
                "event_shapes": Counter(),
                "fight_count": 0,
                "raw_event_count": 0,
                "canonical_mechanic_id": None,
                "review_status": "pending",
                "review_rationale": "",
            },
        )
        if name and name != "(unnamed)":
            row["observed_names"].add(name)
        row["event_shapes"][(raw_type, tick)] += int(count)
        row["fight_count"] = max(int(row["fight_count"]), int(fight_count))
        row["raw_event_count"] += int(count)

    ranked = sorted(
        grouped.values(),
        key=lambda row: (-int(row["fight_count"]), -int(row["raw_event_count"]), int(row["ability_game_id"])),
    )[:limit]
    result: list[dict[str, Any]] = []
    for row in ranked:
        result.append(
            {
                **{key: value for key, value in row.items() if key not in {"observed_names", "event_shapes"}},
                "observed_names": sorted(row["observed_names"]),
                "event_shapes": [
                    {"event_type": event_type, "tick": tick, "count": count}
                    for (event_type, tick), count in sorted(
                        row["event_shapes"].items(), key=lambda item: (-item[1], item[0][0], str(item[0][1]))
                    )
                ],
            }
        )
    return result


def build_review_packet(
    *,
    path: Path,
    bin_seconds: float = 10.0,
    signature_limit: int = 80,
) -> dict[str, Any]:
    if bin_seconds <= 0:
        raise ValueError("bin_seconds must be positive")
    if signature_limit <= 0:
        raise ValueError("signature_limit must be positive")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("corpus must be a JSON object")

    encounter = str(payload.get("encounter") or path.stem.removesuffix("_corpus")).strip()
    fights: list[dict[str, Any]] = []
    kill_count = 0
    wipe_count = 0
    for report_code, fight_id, fight in _fight_rows(payload):
        metadata = _metadata(fight)
        events = _events(fight)
        roster = _roster(fight)
        start, end = _start_end(metadata, events)
        kill = metadata.get("kill")
        kill_count += int(kill is True)
        wipe_count += int(kill is False)
        role_counts = Counter(roster.values())
        fights.append(
            {
                "report_code": report_code,
                "fight_id": fight_id,
                "kill": kill,
                "difficulty": metadata.get("difficulty"),
                "duration_seconds": round(max(0.0, end - start) / 1000.0, 3),
                "event_count": len(events),
                "role_counts": {role: int(role_counts.get(role, 0)) for _key, role in _ROLE_KEYS},
                "observed_primary_target_id": _observed_primary_target(events, set(roster)),
                "pressure_windows": _pressure_windows(fight, bin_seconds=bin_seconds),
            }
        )

    return {
        "schema_version": 1,
        "evidence_status": "candidate_observational_only",
        "purpose": "Human review packet for encounter mechanic strategy research",
        "encounter": encounter,
        "source_path": str(path),
        "report_count": len({row["report_code"] for row in fights}),
        "fight_count": len(fights),
        "kill_count": kill_count,
        "wipe_count": wipe_count,
        "bin_seconds": bin_seconds,
        "review_rules": list(_REVIEW_RULES),
        "fights": fights,
        "candidate_hostile_families": _candidate_families(path, limit=signature_limit),
        "review_state": {
            "canonical_strategy_changed": False,
            "canonical_mechanics_changed": False,
            "pending_human_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-canonical encounter strategy review packet from a raw ESO Logs corpus."
    )
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--bin-seconds", type=float, default=10.0)
    parser.add_argument("--signature-limit", type=int, default=80)
    args = parser.parse_args()

    try:
        packet = build_review_packet(
            path=args.path,
            bin_seconds=args.bin_seconds,
            signature_limit=args.signature_limit,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"REVIEW PACKET ERROR: {exc}")
        return 2

    safe = "_".join(str(packet["encounter"]).casefold().split())
    destination = args.out or Path(f"research/review/{safe}_strategy_review_packet.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PHASE 13 ENCOUNTER STRATEGY REVIEW PACKET")
    print(f"ENCOUNTER: {packet['encounter']}")
    print(f"FIGHTS: {packet['fight_count']} (kills={packet['kill_count']} wipes={packet['wipe_count']})")
    print(f"CANDIDATE_FAMILIES: {len(packet['candidate_hostile_families'])}")
    for row in packet["candidate_hostile_families"][:12]:
        shapes = ",".join(item["event_type"] for item in row["event_shapes"][:5])
        print(
            f"PENDING: ability_id={row['ability_game_id']} fights={row['fight_count']} "
            f"events={row['raw_event_count']} shapes={shapes or 'none'}"
        )
    print(f"OUTPUT: {destination}")
    print("RESULT: observational review packet only; canonical strategy changed: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
