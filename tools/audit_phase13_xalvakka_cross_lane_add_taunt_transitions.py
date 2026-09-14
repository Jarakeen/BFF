from __future__ import annotations

"""Audit report-scoped cross-lane Taunt-state transitions on Xalvakka adds.

The reviewed report-scoped lane assignment tells us which observed source behaved as
boss_holder versus add_handler in this report. This audit does not convert those player
identities into generic MT/OT truth. It asks a narrower question: when both reviewed
lane sources touch the same Iron Atronach or Daedroth instance, do their observed
ability-38254 Taunt-state intervals overlap, or does one begin after the other ends?

No maximum handoff delay is invented. Sequential transitions report their exact gap so
later review can decide whether a repeated shape deserves strategy semantics.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_tank_observed_lane_assignment_service import (
    RotationTankObservedLaneAssignmentService,
)
from services.rotation_tank_observed_taunt_interval_service import (
    ObservedTauntStateEvent,
    RotationTankObservedTauntIntervalService,
)

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"
_REPORT = "XVMgLdq6GpQ7bhKN"
_ENCOUNTER = "xalvakka"
_TARGETS = ("Iron Atronach", "Daedroth")


@dataclass(frozen=True)
class CrossLaneObservation:
    actor_name: str
    fight_id: int
    target_instance: int
    from_lane: str
    to_lane: str
    relation: str
    delta_ms: float


def _events(connection: sqlite3.Connection, *, report_code: str, effect_id: int):
    rows = connection.execute(
        """
        SELECT e.report_code, e.fight_id, a.name AS actor_name,
               COALESCE(e.target_instance, json_extract(e.raw_json, '$.targetInstance'), 0) AS target_instance,
               e.source_id, e.timestamp, e.event_type
        FROM log_event e
        JOIN log_report_actor a
          ON a.report_code = e.report_code
         AND a.actor_id = e.target_id
        WHERE e.report_code = ?
          AND e.ability_game_id = ?
          AND e.event_type IN ('applydebuff', 'removedebuff')
          AND a.name IN ('Iron Atronach', 'Daedroth')
          AND e.source_id IS NOT NULL
        ORDER BY e.fight_id, a.name, target_instance, e.timestamp, e.event_index
        """,
        (report_code, effect_id),
    ).fetchall()
    return tuple(
        ObservedTauntStateEvent(
            report_code=str(row["report_code"]),
            fight_id=int(row["fight_id"]),
            actor_name=str(row["actor_name"]),
            target_instance=int(row["target_instance"] or 0),
            source_id=int(row["source_id"]),
            timestamp_ms=float(row["timestamp"]),
            event_type=str(row["event_type"]),
        )
        for row in rows
    )


def observe(database: Path) -> tuple[CrossLaneObservation, ...]:
    assignment = RotationTankObservedLaneAssignmentService().reviewed_for(
        encounter_id=_ENCOUNTER,
        report_code=_REPORT,
    )
    if assignment is None:
        raise RuntimeError("reviewed Xalvakka observed Tank lane assignment is unavailable")
    source_lane = {row.source_id: row.lane_id for row in assignment.lanes}
    if len(source_lane) < 2:
        return ()

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        events = tuple(
            row
            for row in _events(
                connection,
                report_code=assignment.report_code,
                effect_id=assignment.taunt_state_effect_id,
            )
            if row.source_id in source_lane
        )
    finally:
        connection.close()

    intervals = RotationTankObservedTauntIntervalService().project(events)
    grouped: dict[tuple[int, str, int], list] = {}
    for interval in intervals:
        if interval.source_id not in source_lane:
            continue
        grouped.setdefault(
            (interval.fight_id, interval.actor_name, interval.target_instance), []
        ).append(interval)

    observations: list[CrossLaneObservation] = []
    for (fight_id, actor_name, target_instance), rows in grouped.items():
        sources = {row.source_id for row in rows}
        if len(sources) < 2:
            continue
        ordered = sorted(rows, key=lambda row: (row.start_ms, row.source_id or -1))
        seen_pairs: set[tuple] = set()
        for current in ordered:
            if current.source_id is None:
                continue
            other_rows = [
                row for row in ordered
                if row.source_id is not None and row.source_id != current.source_id
            ]
            for other in other_rows:
                other_end = other.end_ms
                current_end = current.end_ms
                if other_end is not None and other.start_ms <= current.start_ms < other_end:
                    overlap_end = min(
                        other_end,
                        current_end if current_end is not None else other_end,
                    )
                    overlap = max(0.0, overlap_end - current.start_ms)
                    key = (
                        fight_id,
                        actor_name,
                        target_instance,
                        other.source_id,
                        current.source_id,
                        current.start_ms,
                        "overlap",
                    )
                    if overlap > 0 and key not in seen_pairs:
                        seen_pairs.add(key)
                        observations.append(
                            CrossLaneObservation(
                                actor_name=actor_name,
                                fight_id=fight_id,
                                target_instance=target_instance,
                                from_lane=source_lane[int(other.source_id)],
                                to_lane=source_lane[int(current.source_id)],
                                relation="overlap",
                                delta_ms=-overlap,
                            )
                        )
                    break
            else:
                prior = [
                    row for row in other_rows
                    if row.end_ms is not None and row.end_ms <= current.start_ms
                ]
                if not prior:
                    continue
                nearest = max(prior, key=lambda row: float(row.end_ms or 0.0))
                delta = current.start_ms - float(nearest.end_ms)
                key = (
                    fight_id,
                    actor_name,
                    target_instance,
                    nearest.source_id,
                    current.source_id,
                    current.start_ms,
                    "sequential",
                )
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                observations.append(
                    CrossLaneObservation(
                        actor_name=actor_name,
                        fight_id=fight_id,
                        target_instance=target_instance,
                        from_lane=source_lane[int(nearest.source_id)],
                        to_lane=source_lane[int(current.source_id)],
                        relation="sequential",
                        delta_ms=delta,
                    )
                )
    return tuple(observations)


def audit(database: Path) -> tuple[str, ...]:
    assignment = RotationTankObservedLaneAssignmentService().reviewed_for(
        encounter_id=_ENCOUNTER,
        report_code=_REPORT,
    )
    if assignment is None:
        raise RuntimeError("reviewed Xalvakka observed Tank lane assignment is unavailable")
    observations = observe(database)
    lines = [
        "PHASE 13 XALVAKKA CROSS-LANE ADD TAUNT TRANSITION AUDIT",
        f"DATABASE: {database}",
        f"REPORT={assignment.report_code}",
        f"TAUNT_STATE_EFFECT_ID={assignment.taunt_state_effect_id}",
        "SEMANTICS=negative_delta_means_observed_overlap; nonnegative_delta_is_gap_after_other_lane_interval_end",
        f"CROSS_LANE_OBSERVATIONS={len(observations)}",
    ]
    for actor_name in _TARGETS:
        actor_rows = [row for row in observations if row.actor_name == actor_name]
        overlap = [row for row in actor_rows if row.relation == "overlap"]
        sequential = [row for row in actor_rows if row.relation == "sequential"]
        lines.append(
            f"ACTOR_SUMMARY: actor={actor_name} observations={len(actor_rows)} "
            f"overlap={len(overlap)} sequential={len(sequential)}"
        )
        directions = sorted({(row.from_lane, row.to_lane) for row in actor_rows})
        for from_lane, to_lane in directions:
            rows = [
                row for row in actor_rows
                if row.from_lane == from_lane and row.to_lane == to_lane
            ]
            gaps = [row.delta_ms / 1000.0 for row in rows if row.relation == "sequential"]
            overlaps = [-row.delta_ms / 1000.0 for row in rows if row.relation == "overlap"]
            gap_text = (
                f"samples={len(gaps)} median={median(gaps):.3f}s min={min(gaps):.3f}s max={max(gaps):.3f}s"
                if gaps else "samples=0"
            )
            overlap_text = (
                f"samples={len(overlaps)} median={median(overlaps):.3f}s min={min(overlaps):.3f}s max={max(overlaps):.3f}s"
                if overlaps else "samples=0"
            )
            lines.append(
                f"DIRECTION: actor={actor_name} from={from_lane} to={to_lane} "
                f"sequential_gap=[{gap_text}] overlap_duration=[{overlap_text}]"
            )
    for row in observations:
        lines.append(
            f"TRANSITION: fight_id={row.fight_id} actor={row.actor_name} instance={row.target_instance} "
            f"from={row.from_lane} to={row.to_lane} relation={row.relation} delta={row.delta_ms / 1000.0:.3f}s"
        )
    lines.append(
        "INTERPRETATION=cross-lane timing is observational report-scoped cooperation evidence only; no handoff threshold or universal tank-swap policy is promoted"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DATABASE)
    args = parser.parse_args()
    for line in audit(args.db):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
