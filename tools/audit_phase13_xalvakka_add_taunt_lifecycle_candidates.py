from __future__ import annotations

"""Audit target-matched status/debuff events around observed Xalvakka add taunt casts.

Canonical TAUNT cast identities come from the production game database. For each taunt
cast against an Iron Atronach or Daedroth instance, this research audit inspects a small
raw-event window on the same source/target instance for status-like events. The goal is
to discover whether ESO Logs exposes a separate lifecycle effect that can prove taunt
application/removal or ownership duration.

A nearby effect is only a lifecycle *candidate*. Temporal proximity does not prove that
the effect is the taunt state; repeated identity/shape must be reviewed before promotion.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase13_xalvakka_add_earliest_event_signal import observe as observe_add_signals
from tools.audit_phase13_xalvakka_add_taunt_runtime import canonical_taunt_abilities

_DEFAULT_RESEARCH_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_DEFAULT_GAME_DB = ROOT / "data" / "eso.db"
_WINDOW_BEFORE_MS = 250.0
_WINDOW_AFTER_MS = 1500.0
_STATUS_TYPES = {
    "applybuff",
    "removebuff",
    "applybuffstack",
    "removebuffstack",
    "refreshbuff",
    "applydebuff",
    "removedebuff",
    "applydebuffstack",
    "removedebuffstack",
    "refreshdebuff",
}


def _json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _ability_name(raw_json: str | None, ability_id: int | None) -> str:
    payload = _json(raw_json)
    for key in ("abilityName", "ability_name", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    ability = payload.get("ability")
    if isinstance(ability, str) and ability.strip():
        return ability.strip()
    if isinstance(ability, dict):
        for key in ("name", "nameEnglish", "displayName"):
            value = ability.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"ability-{ability_id}" if ability_id is not None else "unknown"


@dataclass(frozen=True)
class LifecycleCandidate:
    report_code: str
    fight_id: int
    actor_name: str
    instance_id: int
    cast_time_ms: float
    cast_ability_id: int
    cast_ability_name: str
    source_id: int | None
    event_time_ms: float
    event_type: str
    effect_ability_id: int | None
    effect_ability_name: str

    @property
    def offset_ms(self) -> float:
        return self.event_time_ms - self.cast_time_ms


def observe(
    research_db: Path,
    game_db: Path,
    *,
    before_ms: float = _WINDOW_BEFORE_MS,
    after_ms: float = _WINDOW_AFTER_MS,
) -> tuple[LifecycleCandidate, ...]:
    taunts = canonical_taunt_abilities(game_db)
    taunt_by_id = {row.ability_id: row.skill_name for row in taunts}
    ability_ids = tuple(sorted(taunt_by_id))
    if not ability_ids:
        raise ValueError("canonical game database exposes no TAUNT skill-rank ability IDs")

    adds = observe_add_signals(research_db)
    db = sqlite3.connect(f"file:{research_db.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in ability_ids)
        status_placeholders = ",".join("?" for _ in _STATUS_TYPES)
        candidates: list[LifecycleCandidate] = []
        for add in adds:
            casts = db.execute(
                f"""
                SELECT timestamp, source_id, ability_game_id, raw_json
                FROM log_event
                WHERE report_code=? AND fight_id=?
                  AND lower(event_type)='cast'
                  AND source_is_friendly=1
                  AND target_is_friendly=0
                  AND target_id=?
                  AND COALESCE(target_instance, CAST(json_extract(raw_json, '$.targetInstance') AS INTEGER), 0)=?
                  AND ability_game_id IN ({placeholders})
                ORDER BY timestamp, event_index
                """,
                (add.report_code, add.fight_id, add.actor_id, add.instance_id, *ability_ids),
            ).fetchall()
            for cast in casts:
                cast_time = float(cast["timestamp"])
                source_id = cast["source_id"]
                status_rows = db.execute(
                    f"""
                    SELECT timestamp, event_type, ability_game_id, raw_json
                    FROM log_event
                    WHERE report_code=? AND fight_id=?
                      AND timestamp BETWEEN ? AND ?
                      AND lower(event_type) IN ({status_placeholders})
                      AND target_id=?
                      AND COALESCE(target_instance, CAST(json_extract(raw_json, '$.targetInstance') AS INTEGER), 0)=?
                      AND (? IS NULL OR source_id=?)
                    ORDER BY timestamp, event_index
                    """,
                    (
                        add.report_code,
                        add.fight_id,
                        cast_time - float(before_ms),
                        cast_time + float(after_ms),
                        *sorted(_STATUS_TYPES),
                        add.actor_id,
                        add.instance_id,
                        source_id,
                        source_id,
                    ),
                ).fetchall()
                cast_id = int(cast["ability_game_id"])
                for event in status_rows:
                    effect_id = (
                        None
                        if event["ability_game_id"] is None
                        else int(event["ability_game_id"])
                    )
                    candidates.append(
                        LifecycleCandidate(
                            report_code=add.report_code,
                            fight_id=add.fight_id,
                            actor_name=add.actor_name,
                            instance_id=add.instance_id,
                            cast_time_ms=cast_time,
                            cast_ability_id=cast_id,
                            cast_ability_name=taunt_by_id[cast_id],
                            source_id=None if source_id is None else int(source_id),
                            event_time_ms=float(event["timestamp"]),
                            event_type=str(event["event_type"]),
                            effect_ability_id=effect_id,
                            effect_ability_name=_ability_name(event["raw_json"], effect_id),
                        )
                    )
        return tuple(candidates)
    finally:
        db.close()


def audit(research_db: Path, game_db: Path) -> tuple[str, ...]:
    rows = observe(research_db, game_db)
    lines = [
        "PHASE 13 XALVAKKA ADD TAUNT LIFECYCLE CANDIDATE AUDIT",
        f"RESEARCH_DATABASE: {research_db}",
        f"GAME_DATABASE: {game_db}",
        f"WINDOW=-{_WINDOW_BEFORE_MS / 1000.0:.3f}s/+{_WINDOW_AFTER_MS / 1000.0:.3f}s",
        f"LIFECYCLE_CANDIDATE_EVENTS={len(rows)}",
    ]

    identity_counts: Counter[tuple[int | None, str, str]] = Counter()
    actor_counts: defaultdict[tuple[int | None, str, str], Counter[str]] = defaultdict(Counter)
    offsets: defaultdict[tuple[int | None, str, str], list[float]] = defaultdict(list)
    for row in rows:
        key = (row.effect_ability_id, row.effect_ability_name, row.event_type)
        identity_counts[key] += 1
        actor_counts[key][row.actor_name] += 1
        offsets[key].append(row.offset_ms / 1000.0)

    for key, count in identity_counts.most_common():
        effect_id, effect_name, event_type = key
        actor_text = ",".join(
            f"{actor}={value}" for actor, value in sorted(actor_counts[key].items())
        )
        values = offsets[key]
        lines.append(
            "CANDIDATE_EFFECT: "
            f"ability={effect_name} ability_id={effect_id} event={event_type} count={count} "
            f"offset_min={min(values):.3f}s offset_max={max(values):.3f}s actors=[{actor_text}]"
        )

    # Print a bounded sample so exact source/cast/effect relationships remain inspectable.
    for row in rows[:80]:
        lines.append(
            "LIFECYCLE_EVENT: "
            f"report={row.report_code} fight_id={row.fight_id} actor={row.actor_name} "
            f"instance={row.instance_id} source_id={row.source_id} "
            f"cast={row.cast_ability_name}:{row.cast_ability_id} "
            f"effect={row.effect_ability_name}:{row.effect_ability_id} "
            f"event={row.event_type} offset={row.offset_ms / 1000.0:.3f}s"
        )

    lines.append(
        "INTERPRETATION=nearby status events are taunt-lifecycle candidates only; repeated target-matched identity and lifecycle shape must be reviewed before continuous ownership is promoted"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_RESEARCH_DB)
    parser.add_argument("--game-db", type=Path, default=_DEFAULT_GAME_DB)
    args = parser.parse_args()
    for path in (args.db, args.game_db):
        if not path.exists():
            print(f"AUDIT ERROR: database does not exist: {path}")
            return 2
    try:
        lines = audit(args.db, args.game_db)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
