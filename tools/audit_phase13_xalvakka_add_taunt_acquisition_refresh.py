from __future__ import annotations

"""Audit observed Xalvakka add taunt acquisition and repeat-cast behavior.

The add activity audit supplies the reviewed observational entry boundary. Canonical
TAUNT skill-rank ability IDs come from the production game database. This audit then
uses taunt *cast* events as action anchors per named add instance.

A first taunt cast proves observed acquisition action. Later casts prove observed repeat
taunt actions. Neither proves uninterrupted aggro ownership between casts; that still
requires lifecycle/threat evidence.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase13_xalvakka_add_earliest_event_signal import observe as observe_add_signals
from tools.audit_phase13_xalvakka_add_taunt_runtime import canonical_taunt_abilities

_DEFAULT_RESEARCH_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_DEFAULT_GAME_DB = ROOT / "data" / "eso.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")


@dataclass(frozen=True)
class AddTauntActionObservation:
    report_code: str
    fight_id: int
    actor_name: str
    actor_id: int
    instance_id: int
    activity_boundary_ms: float
    first_taunt_cast_ms: float | None
    taunt_cast_times_ms: tuple[float, ...]
    taunt_sources: tuple[int, ...]

    @property
    def acquisition_lag_ms(self) -> float | None:
        if self.first_taunt_cast_ms is None:
            return None
        return self.first_taunt_cast_ms - self.activity_boundary_ms

    @property
    def refresh_intervals_ms(self) -> tuple[float, ...]:
        return tuple(
            right - left
            for left, right in zip(self.taunt_cast_times_ms, self.taunt_cast_times_ms[1:])
        )


def _open_read_only(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def observe(research_db: Path, game_db: Path) -> tuple[AddTauntActionObservation, ...]:
    taunts = canonical_taunt_abilities(game_db)
    ability_ids = tuple(sorted(row.ability_id for row in taunts))
    if not ability_ids:
        raise ValueError("canonical game database exposes no TAUNT skill-rank ability IDs")

    add_rows = observe_add_signals(research_db)
    db = _open_read_only(research_db)
    try:
        placeholders = ",".join("?" for _ in ability_ids)
        observations: list[AddTauntActionObservation] = []
        for add in add_rows:
            boundary = add.first_source_ms if add.first_source_ms is not None else add.first_involving_ms
            if boundary is None:
                continue
            rows = db.execute(
                f"""
                SELECT timestamp, source_id
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
                (
                    add.report_code,
                    add.fight_id,
                    add.actor_id,
                    add.instance_id,
                    *ability_ids,
                ),
            ).fetchall()
            times = tuple(float(row["timestamp"]) for row in rows)
            sources = tuple(
                dict.fromkeys(
                    int(row["source_id"])
                    for row in rows
                    if row["source_id"] is not None
                )
            )
            observations.append(
                AddTauntActionObservation(
                    report_code=add.report_code,
                    fight_id=add.fight_id,
                    actor_name=add.actor_name,
                    actor_id=add.actor_id,
                    instance_id=add.instance_id,
                    activity_boundary_ms=float(boundary),
                    first_taunt_cast_ms=times[0] if times else None,
                    taunt_cast_times_ms=times,
                    taunt_sources=sources,
                )
            )
        return tuple(observations)
    finally:
        db.close()


def _source_labels(db: sqlite3.Connection) -> dict[tuple[str, int], str]:
    rows = db.execute(
        "SELECT report_code, actor_id, name, display_name FROM log_report_actor"
    ).fetchall()
    result: dict[tuple[str, int], str] = {}
    for row in rows:
        label = str(row["name"] or row["display_name"] or f"actor-{row['actor_id']}").strip()
        result[(str(row["report_code"]), int(row["actor_id"]))] = label
    return result


def _summary(values_ms: tuple[float, ...]) -> str:
    if not values_ms:
        return "samples=0"
    values = tuple(value / 1000.0 for value in values_ms)
    return (
        f"samples={len(values)} median={statistics.median(values):.3f}s "
        f"min={min(values):.3f}s max={max(values):.3f}s"
    )


def audit(research_db: Path, game_db: Path) -> tuple[str, ...]:
    rows = observe(research_db, game_db)
    db = _open_read_only(research_db)
    try:
        source_labels = _source_labels(db)
    finally:
        db.close()

    lines = [
        "PHASE 13 XALVAKKA ADD TAUNT ACQUISITION/REFRESH AUDIT",
        f"RESEARCH_DATABASE: {research_db}",
        f"GAME_DATABASE: {game_db}",
        f"OBSERVED_ADD_INSTANCES: {len(rows)}",
    ]

    for actor_name in _TARGET_NAMES:
        actor_rows = tuple(row for row in rows if row.actor_name == actor_name)
        taunted = tuple(row for row in actor_rows if row.first_taunt_cast_ms is not None)
        acquisition = tuple(
            row.acquisition_lag_ms
            for row in taunted
            if row.acquisition_lag_ms is not None
        )
        refreshes = tuple(
            interval
            for row in taunted
            for interval in row.refresh_intervals_ms
        )
        lines.append(
            f"ACTOR_SUMMARY: actor={actor_name} instances={len(actor_rows)} "
            f"taunted_instances={len(taunted)} untaunted_instances={len(actor_rows) - len(taunted)}"
        )
        lines.append(
            f"ACQUISITION_LAG_FROM_ACTIVITY: actor={actor_name} {_summary(acquisition)}"
        )
        lines.append(
            f"REPEAT_TAUNT_INTERVAL: actor={actor_name} {_summary(refreshes)}"
        )

    for row in rows:
        lag = "none" if row.acquisition_lag_ms is None else f"{row.acquisition_lag_ms / 1000.0:.3f}s"
        sources = ",".join(
            f"{source_id}:{source_labels.get((row.report_code, source_id), 'unknown')}"
            for source_id in row.taunt_sources
        ) or "none"
        intervals = ",".join(f"{value / 1000.0:.3f}s" for value in row.refresh_intervals_ms) or "none"
        lines.append(
            "ADD_TAUNT_ACTIONS: "
            f"report={row.report_code} fight_id={row.fight_id} actor={row.actor_name} "
            f"instance={row.instance_id} casts={len(row.taunt_cast_times_ms)} "
            f"acquisition_lag={lag} sources={sources} repeat_intervals=[{intervals}]"
        )

    taunted_total = sum(row.first_taunt_cast_ms is not None for row in rows)
    repeated_total = sum(len(row.taunt_cast_times_ms) > 1 for row in rows)
    lines.append(f"TAUNTED_ADD_INSTANCES={taunted_total}")
    lines.append(f"REPEATED_TAUNT_ADD_INSTANCES={repeated_total}")
    lines.append(
        "INTERPRETATION=first canonical TAUNT cast proves observed acquisition action and later casts prove repeat taunt actions; intervals do not prove continuous aggro ownership"
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
        for line in audit(args.db, args.game_db):
            print(line)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
