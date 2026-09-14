from __future__ import annotations

"""Align observed Xalvakka add activity with reviewed retreat/resume runtime evidence.

Research only. Add ``first_damage`` is an observational lower bound on target activity,
not exact spawn, targetable, aggro, or taunt-required timing. The audit classifies those
observations against observed Xalvakka active/transition boundaries and summarizes
recurrence without promoting rotation policy.
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

from tools.audit_phase13_xalvakka_transition_resume_runtime import observe as observe_transitions

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")


@dataclass(frozen=True)
class AddObservation:
    report_code: str
    fight_id: int
    name: str
    target_instance: int
    first_damage_ms: float
    last_damage_ms: float
    fight_start_ms: float

    @property
    def first_relative_seconds(self) -> float:
        return (self.first_damage_ms - self.fight_start_ms) / 1000.0


@dataclass(frozen=True)
class PhaseBoundaries:
    crossing_70_ms: float | None = None
    resume_70_ms: float | None = None
    crossing_40_ms: float | None = None
    resume_40_ms: float | None = None


def classify_phase(timestamp_ms: float, boundaries: PhaseBoundaries) -> str:
    if boundaries.crossing_70_ms is None or timestamp_ms < boundaries.crossing_70_ms:
        return "phase_1"
    if boundaries.resume_70_ms is None or timestamp_ms < boundaries.resume_70_ms:
        return "transition_70"
    if boundaries.crossing_40_ms is None or timestamp_ms < boundaries.crossing_40_ms:
        return "phase_2"
    if boundaries.resume_40_ms is None or timestamp_ms < boundaries.resume_40_ms:
        return "transition_40"
    return "phase_3"


def cluster_wave_times(seconds: tuple[float, ...], *, maximum_gap_seconds: float = 5.0) -> tuple[tuple[float, ...], ...]:
    if maximum_gap_seconds < 0:
        raise ValueError("maximum_gap_seconds must be non-negative")
    if not seconds:
        return ()
    ordered = tuple(sorted(float(value) for value in seconds))
    waves: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - waves[-1][-1] <= maximum_gap_seconds:
            waves[-1].append(value)
        else:
            waves.append([value])
    return tuple(tuple(wave) for wave in waves)


def recurrence_intervals(seconds: tuple[float, ...]) -> tuple[float, ...]:
    ordered = tuple(sorted(float(value) for value in seconds))
    return tuple(right - left for left, right in zip(ordered, ordered[1:]))


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _add_observations(db: sqlite3.Connection) -> tuple[AddObservation, ...]:
    rows = db.execute(
        """
        SELECT f.report_code, f.fight_id, f.start_time,
               a.name, COALESCE(e.target_instance, 0) AS target_instance,
               MIN(e.timestamp) AS first_damage, MAX(e.timestamp) AS last_damage
        FROM log_fight AS f
        JOIN log_event AS e
          ON e.report_code=f.report_code AND e.fight_id=f.fight_id
        JOIN log_report_actor AS a
          ON a.report_code=e.report_code AND a.actor_id=e.target_id
        WHERE lower(trim(f.name))='xalvakka'
          AND a.name IN (?, ?)
          AND e.event_type='damage'
          AND e.source_is_friendly=1
          AND e.target_is_friendly=0
        GROUP BY f.report_code, f.fight_id, f.start_time, a.name,
                 e.target_id, COALESCE(e.target_instance, 0)
        ORDER BY f.report_code, f.fight_id, first_damage
        """,
        _TARGET_NAMES,
    ).fetchall()
    return tuple(
        AddObservation(
            report_code=str(row["report_code"]),
            fight_id=int(row["fight_id"]),
            name=str(row["name"]),
            target_instance=int(row["target_instance"]),
            first_damage_ms=float(row["first_damage"]),
            last_damage_ms=float(row["last_damage"]),
            fight_start_ms=float(row["start_time"] or 0.0),
        )
        for row in rows
    )


def audit(database: Path, *, wave_gap_seconds: float = 5.0) -> tuple[str, ...]:
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    try:
        missing = {name for name in ("log_fight", "log_event", "log_report_actor") if not _table_exists(db, name)}
        if missing:
            return ("UNRESOLVED: missing runtime tables: " + ", ".join(sorted(missing)),)
        adds = _add_observations(db)
    finally:
        db.close()

    transitions = observe_transitions(database)
    transition_by_fight: dict[tuple[str, int], PhaseBoundaries] = {}
    for row in transitions:
        key = (row.report_code, row.fight_id)
        current = transition_by_fight.get(key, PhaseBoundaries())
        if abs(row.threshold_fraction - 0.70) < 1e-9:
            current = PhaseBoundaries(
                crossing_70_ms=row.crossing_time_ms,
                resume_70_ms=row.resume_time_ms,
                crossing_40_ms=current.crossing_40_ms,
                resume_40_ms=current.resume_40_ms,
            )
        elif abs(row.threshold_fraction - 0.40) < 1e-9:
            current = PhaseBoundaries(
                crossing_70_ms=current.crossing_70_ms,
                resume_70_ms=current.resume_70_ms,
                crossing_40_ms=row.crossing_time_ms,
                resume_40_ms=row.resume_time_ms,
            )
        transition_by_fight[key] = current

    lines = [
        "PHASE 13 XALVAKKA ADD PHASE ALIGNMENT AUDIT",
        f"DATABASE: {database}",
        f"OBSERVED_ADD_INSTANCES: {len(adds)}",
        f"DAEDROTH_WAVE_CLUSTER_GAP_SECONDS: {wave_gap_seconds:g}",
    ]

    phase_counts: dict[tuple[str, str], int] = {}
    recurrence_by_name: dict[str, list[float]] = {name: [] for name in _TARGET_NAMES}
    grouped: dict[tuple[str, int, str], list[AddObservation]] = {}
    for row in adds:
        grouped.setdefault((row.report_code, row.fight_id, row.name), []).append(row)
        phase = classify_phase(
            row.first_damage_ms,
            transition_by_fight.get((row.report_code, row.fight_id), PhaseBoundaries()),
        )
        phase_counts[(row.name, phase)] = phase_counts.get((row.name, phase), 0) + 1

    for (report_code, fight_id, name), rows in sorted(grouped.items()):
        firsts = tuple(row.first_relative_seconds for row in rows)
        intervals = recurrence_intervals(firsts)
        recurrence_by_name[name].extend(intervals)
        boundary = transition_by_fight.get((report_code, fight_id), PhaseBoundaries())
        labels = tuple(classify_phase(row.first_damage_ms, boundary) for row in rows)
        detail = ", ".join(f"{time:.3f}s:{label}" for time, label in zip(firsts, labels))
        lines.append(f"FIGHT_ADD_ACTIVITY: report={report_code} fight_id={fight_id} actor={name} first_damage=[{detail}]")
        if name == "Daedroth":
            waves = cluster_wave_times(firsts, maximum_gap_seconds=wave_gap_seconds)
            rendered = "; ".join(
                "[" + ", ".join(f"{value:.3f}s" for value in wave) + "]" for wave in waves
            )
            lines.append(f"DAEDROTH_WAVES: report={report_code} fight_id={fight_id} waves={rendered}")

    for name in _TARGET_NAMES:
        intervals = tuple(recurrence_by_name[name])
        if intervals:
            lines.append(
                f"RECURRENCE_OBSERVED: actor={name} samples={len(intervals)} "
                f"median={statistics.median(intervals):.3f}s "
                f"min={min(intervals):.3f}s max={max(intervals):.3f}s"
            )
        counts = ", ".join(
            f"{phase}={phase_counts[(name, phase)]}"
            for phase in ("phase_1", "transition_70", "phase_2", "transition_40", "phase_3")
            if (name, phase) in phase_counts
        )
        lines.append(f"PHASE_COUNTS: actor={name} {counts or 'none'}")

    lines.append(
        "INTERPRETATION=phase alignment and recurrence are observational first-damage evidence only; do not promote exact spawn or taunt-required clocks without stronger event evidence"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DATABASE)
    parser.add_argument("--wave-gap-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.wave_gap_seconds < 0:
        parser.error("--wave-gap-seconds must be non-negative")
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    for line in audit(args.db, wave_gap_seconds=args.wave_gap_seconds):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
