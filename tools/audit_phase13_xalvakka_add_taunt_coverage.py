from __future__ import annotations

"""Audit exact observed taunt-state coverage across Xalvakka add active lifetimes.

Observed add lifetime uses the earliest reviewed add-activity boundary as start and the
last raw event involving the same NPC instance as the observational end. Reviewed taunt
state intervals come from ability 38254 lifecycle events. Coverage unions all taunt-state
intervals across sources, while source-specific spans remain visible for transfer review.

This audit does not equate the last observed event with exact death/despawn. It reports
observational coverage and gaps only.
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import statistics

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")
_TAUNT_EFFECT_ID = 38254


@dataclass(frozen=True)
class Span:
    start_ms: float
    end_ms: float
    source_id: int | None = None

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.end_ms - self.start_ms)


@dataclass(frozen=True)
class CoverageRow:
    report_code: str
    fight_id: int
    actor_name: str
    actor_id: int
    instance_id: int
    active_start_ms: float
    active_end_ms: float
    taunt_spans: tuple[Span, ...]
    merged_spans: tuple[Span, ...]
    gaps: tuple[Span, ...]
    sources: tuple[int, ...]

    @property
    def active_duration_ms(self) -> float:
        return max(0.0, self.active_end_ms - self.active_start_ms)

    @property
    def covered_ms(self) -> float:
        return sum(span.duration_ms for span in self.merged_spans)

    @property
    def coverage_fraction(self) -> float:
        if self.active_duration_ms <= 0:
            return 0.0
        return min(1.0, self.covered_ms / self.active_duration_ms)


def _open(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _source_instance_expr() -> str:
    return "COALESCE(CAST(json_extract(raw_json, '$.sourceInstance') AS INTEGER), 0)"


def _target_instance_expr() -> str:
    return "COALESCE(target_instance, CAST(json_extract(raw_json, '$.targetInstance') AS INTEGER), 0)"


def _merge(spans: tuple[Span, ...], *, start_ms: float, end_ms: float) -> tuple[Span, ...]:
    clipped = sorted(
        (
            Span(max(start_ms, span.start_ms), min(end_ms, span.end_ms), None)
            for span in spans
            if min(end_ms, span.end_ms) > max(start_ms, span.start_ms)
        ),
        key=lambda span: (span.start_ms, span.end_ms),
    )
    if not clipped:
        return ()
    merged: list[Span] = [clipped[0]]
    for span in clipped[1:]:
        last = merged[-1]
        if span.start_ms <= last.end_ms:
            merged[-1] = Span(last.start_ms, max(last.end_ms, span.end_ms), None)
        else:
            merged.append(span)
    return tuple(merged)


def _gaps(merged: tuple[Span, ...], *, start_ms: float, end_ms: float) -> tuple[Span, ...]:
    cursor = start_ms
    result: list[Span] = []
    for span in merged:
        if span.start_ms > cursor:
            result.append(Span(cursor, span.start_ms, None))
        cursor = max(cursor, span.end_ms)
    if cursor < end_ms:
        result.append(Span(cursor, end_ms, None))
    return tuple(result)


def observe(database: Path) -> tuple[CoverageRow, ...]:
    db = _open(database)
    try:
        actor_rows = db.execute(
            "SELECT report_code, actor_id, name FROM log_report_actor WHERE name IN (?, ?)",
            _TARGET_NAMES,
        ).fetchall()
        actor_map = {
            (str(row["report_code"]), int(row["actor_id"])): str(row["name"])
            for row in actor_rows
        }

        fights = db.execute(
            "SELECT report_code, fight_id FROM log_fight WHERE lower(trim(name))='xalvakka' ORDER BY report_code, fight_id"
        ).fetchall()
        rows: list[CoverageRow] = []
        for fight in fights:
            report = str(fight["report_code"])
            fight_id = int(fight["fight_id"])
            actor_ids = tuple(actor_id for (code, actor_id), _ in actor_map.items() if code == report)
            if not actor_ids:
                continue
            placeholders = ",".join("?" for _ in actor_ids)

            # Discover every observed target instance from friendly damage so this stays
            # aligned with the existing 45-instance research sample.
            instances = db.execute(
                f"""
                SELECT target_id AS actor_id,
                       {_target_instance_expr()} AS instance_id,
                       MIN(timestamp) AS first_friendly_damage
                FROM log_event
                WHERE report_code=? AND fight_id=?
                  AND event_type='damage'
                  AND source_is_friendly=1 AND target_is_friendly=0
                  AND target_id IN ({placeholders})
                GROUP BY target_id, instance_id
                ORDER BY first_friendly_damage
                """,
                (report, fight_id, *actor_ids),
            ).fetchall()

            for inst in instances:
                actor_id = int(inst["actor_id"])
                instance_id = int(inst["instance_id"] or 0)

                involving = db.execute(
                    f"""
                    SELECT MIN(timestamp), MAX(timestamp)
                    FROM log_event
                    WHERE report_code=? AND fight_id=? AND (
                        (source_id=? AND {_source_instance_expr()}=?) OR
                        (target_id=? AND {_target_instance_expr()}=?)
                    )
                    """,
                    (report, fight_id, actor_id, instance_id, actor_id, instance_id),
                ).fetchone()
                if involving[0] is None or involving[1] is None:
                    continue
                active_start = float(involving[0])
                active_end = float(involving[1])

                lifecycle = db.execute(
                    f"""
                    SELECT timestamp, lower(event_type) AS event_type, source_id
                    FROM log_event
                    WHERE report_code=? AND fight_id=?
                      AND target_id=? AND {_target_instance_expr()}=?
                      AND ability_game_id=?
                      AND lower(event_type) IN ('applydebuff','removedebuff')
                    ORDER BY timestamp, event_index
                    """,
                    (report, fight_id, actor_id, instance_id, _TAUNT_EFFECT_ID),
                ).fetchall()

                open_by_source: dict[int | None, float] = {}
                spans: list[Span] = []
                sources: set[int] = set()
                for event in lifecycle:
                    source_id = None if event["source_id"] is None else int(event["source_id"])
                    when = float(event["timestamp"])
                    if source_id is not None:
                        sources.add(source_id)
                    if str(event["event_type"]) == "applydebuff":
                        prior = open_by_source.get(source_id)
                        if prior is not None and when > prior:
                            spans.append(Span(prior, when, source_id))
                        open_by_source[source_id] = when
                    elif str(event["event_type"]) == "removedebuff":
                        prior = open_by_source.pop(source_id, None)
                        if prior is not None and when >= prior:
                            spans.append(Span(prior, when, source_id))
                for source_id, start in open_by_source.items():
                    spans.append(Span(start, active_end, source_id))

                merged = _merge(tuple(spans), start_ms=active_start, end_ms=active_end)
                gaps = _gaps(merged, start_ms=active_start, end_ms=active_end)
                rows.append(
                    CoverageRow(
                        report_code=report,
                        fight_id=fight_id,
                        actor_name=actor_map[(report, actor_id)],
                        actor_id=actor_id,
                        instance_id=instance_id,
                        active_start_ms=active_start,
                        active_end_ms=active_end,
                        taunt_spans=tuple(spans),
                        merged_spans=merged,
                        gaps=gaps,
                        sources=tuple(sorted(sources)),
                    )
                )
        return tuple(rows)
    finally:
        db.close()


def _summary(values: tuple[float, ...]) -> str:
    if not values:
        return "samples=0"
    return (
        f"samples={len(values)} median={statistics.median(values):.1f}% "
        f"min={min(values):.1f}% max={max(values):.1f}%"
    )


def audit(database: Path) -> tuple[str, ...]:
    rows = observe(database)
    lines = [
        "PHASE 13 XALVAKKA ADD TAUNT COVERAGE AUDIT",
        f"DATABASE: {database}",
        f"OBSERVED_ADD_INSTANCES: {len(rows)}",
        "ACTIVE_WINDOW=earliest_to_latest_raw_event_involving_same_add_instance",
        "TAUNT_STATE=ability_38254_applydebuff_to_removedebuff",
    ]
    for actor in _TARGET_NAMES:
        actor_rows = tuple(row for row in rows if row.actor_name == actor)
        coverage = tuple(row.coverage_fraction * 100.0 for row in actor_rows)
        multi_source = sum(len(row.sources) > 1 for row in actor_rows)
        untaunted = sum(not row.merged_spans for row in actor_rows)
        lines.append(
            f"ACTOR_SUMMARY: actor={actor} instances={len(actor_rows)} "
            f"untaunted={untaunted} multi_source={multi_source} coverage={_summary(coverage)}"
        )

    for row in rows:
        gap_seconds = tuple(g.duration_ms / 1000.0 for g in row.gaps)
        longest_gap = max(gap_seconds) if gap_seconds else 0.0
        source_text = ",".join(str(value) for value in row.sources) or "none"
        lines.append(
            "ADD_COVERAGE: "
            f"report={row.report_code} fight_id={row.fight_id} actor={row.actor_name} "
            f"instance={row.instance_id} active={row.active_duration_ms / 1000.0:.3f}s "
            f"taunted={row.covered_ms / 1000.0:.3f}s coverage={row.coverage_fraction * 100.0:.1f}% "
            f"gaps={len(row.gaps)} longest_gap={longest_gap:.3f}s sources={source_text}"
        )
    lines.append(
        "INTERPRETATION=coverage is observational taunt-state occupancy over the raw-event activity window; last observed event is not promoted to exact death/despawn"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    try:
        for line in audit(args.db):
            print(line)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
