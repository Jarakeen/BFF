from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from statistics import median


@dataclass(frozen=True)
class RotationUnnervingBoneyardCadenceStabilityReport:
    track_count: int
    occurrence_count: int
    interval_count: int
    median_interval_seconds: float | None
    p10_interval_seconds: float | None
    p90_interval_seconds: float | None
    minimum_interval_seconds: float | None
    maximum_interval_seconds: float | None
    near_one_second_count: int
    near_one_second_fraction: float | None
    unresolved: tuple[str, ...] = ()


class RotationUnnervingBoneyardCadenceStabilityService:
    """Review cadence of Boneyard evidence ID 117809 after occurrence normalization.

    Same-cast-track damage rows within ``collapse_tolerance_ms`` are treated as one
    observable occurrence before intervals are measured. This is research-only and never
    promotes executable periodic semantics automatically.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        candidate_ability_id: int = 117809,
        collapse_tolerance_ms: float = 10.0,
        one_second_tolerance_seconds: float = 0.08,
    ) -> RotationUnnervingBoneyardCadenceStabilityReport:
        if not self.logs_database_path.is_file():
            return self._report(
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",)
            )
        if collapse_tolerance_ms < 0 or one_second_tolerance_seconds < 0:
            return self._report(unresolved=("tolerances must be non-negative",))

        with self._open_logs() as db:
            error = self._schema_error(db)
            if error:
                return self._report(unresolved=(error,))
            rows = db.execute(
                "SELECT report_code,fight_id,source_id,cast_track_id,timestamp,event_index "
                "FROM log_event WHERE ability_game_id=? AND lower(event_type)='damage' "
                "AND cast_track_id IS NOT NULL "
                "ORDER BY report_code,fight_id,source_id,cast_track_id,timestamp,event_index",
                (int(candidate_ability_id),),
            ).fetchall()

        grouped: dict[tuple[str, int, int, int], list[float]] = {}
        for row in rows:
            if row["source_id"] is None:
                continue
            key = (
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
                int(row["cast_track_id"]),
            )
            grouped.setdefault(key, []).append(float(row["timestamp"]))

        occurrence_count = 0
        intervals: list[float] = []
        track_count = 0
        collapse_tolerance = float(collapse_tolerance_ms)
        for timestamps in grouped.values():
            if not timestamps:
                continue
            ordered = sorted(timestamps)
            occurrences = [ordered[0]]
            for value in ordered[1:]:
                if value - occurrences[-1] <= collapse_tolerance:
                    continue
                occurrences.append(value)
            if not occurrences:
                continue
            track_count += 1
            occurrence_count += len(occurrences)
            intervals.extend(
                (right - left) / 1000.0
                for left, right in zip(occurrences, occurrences[1:])
                if right > left
            )

        if not intervals:
            return self._report(
                track_count=track_count,
                occurrence_count=occurrence_count,
                unresolved=("no normalized adjacent 117809 intervals were observed",),
            )

        ordered_intervals = sorted(intervals)
        p10 = self._percentile(ordered_intervals, 0.10)
        p90 = self._percentile(ordered_intervals, 0.90)
        tolerance = float(one_second_tolerance_seconds)
        near_one = sum(1 for value in ordered_intervals if abs(value - 1.0) <= tolerance)
        return RotationUnnervingBoneyardCadenceStabilityReport(
            track_count=track_count,
            occurrence_count=occurrence_count,
            interval_count=len(ordered_intervals),
            median_interval_seconds=float(median(ordered_intervals)),
            p10_interval_seconds=p10,
            p90_interval_seconds=p90,
            minimum_interval_seconds=ordered_intervals[0],
            maximum_interval_seconds=ordered_intervals[-1],
            near_one_second_count=near_one,
            near_one_second_fraction=near_one / len(ordered_intervals),
            unresolved=(),
        )

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float:
        if len(values) == 1:
            return float(values[0])
        position = (len(values) - 1) * float(fraction)
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        weight = position - lower
        return float(values[lower] * (1.0 - weight) + values[upper] * weight)

    @staticmethod
    def _report(
        *,
        track_count: int = 0,
        occurrence_count: int = 0,
        unresolved: tuple[str, ...] = (),
    ) -> RotationUnnervingBoneyardCadenceStabilityReport:
        return RotationUnnervingBoneyardCadenceStabilityReport(
            track_count=track_count,
            occurrence_count=occurrence_count,
            interval_count=0,
            median_interval_seconds=None,
            p10_interval_seconds=None,
            p90_interval_seconds=None,
            minimum_interval_seconds=None,
            maximum_interval_seconds=None,
            near_one_second_count=0,
            near_one_second_fraction=None,
            unresolved=unresolved,
        )

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'").fetchone()
        if table is None:
            return "log_event table is unavailable"
        required = {
            "report_code", "fight_id", "event_index", "timestamp", "event_type",
            "source_id", "ability_game_id", "cast_track_id",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None


__all__ = [
    "RotationUnnervingBoneyardCadenceStabilityReport",
    "RotationUnnervingBoneyardCadenceStabilityService",
]
