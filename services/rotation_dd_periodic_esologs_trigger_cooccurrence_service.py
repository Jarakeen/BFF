from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class TriggerCoincidentPeriodicObservation:
    report_code: str
    fight_id: int
    source_id: int
    trigger_event_index: int
    trigger_timestamp_ms: float
    trigger_target_id: int | None
    trigger_hit_type: str | None
    trigger_amount: float | None
    trigger_cast_track_id: int | None
    periodic_event_index: int
    periodic_timestamp_ms: float
    periodic_target_id: int | None
    periodic_hit_type: str | None
    periodic_amount: float | None
    periodic_tick: bool | None
    periodic_cast_track_id: int | None
    next_periodic_event_index: int | None = None
    next_periodic_timestamp_ms: float | None = None
    next_periodic_target_id: int | None = None
    next_periodic_hit_type: str | None = None
    next_periodic_amount: float | None = None
    next_periodic_tick: bool | None = None

    @property
    def offset_seconds(self) -> float:
        return (self.periodic_timestamp_ms - self.trigger_timestamp_ms) / 1000.0

    @property
    def next_offset_seconds(self) -> float | None:
        if self.next_periodic_timestamp_ms is None:
            return None
        return (self.next_periodic_timestamp_ms - self.trigger_timestamp_ms) / 1000.0

    @property
    def same_target(self) -> bool | None:
        if self.trigger_target_id is None or self.periodic_target_id is None:
            return None
        return self.trigger_target_id == self.periodic_target_id

    @property
    def same_cast_track(self) -> bool | None:
        if self.trigger_cast_track_id is None or self.periodic_cast_track_id is None:
            return None
        return self.trigger_cast_track_id == self.periodic_cast_track_id


@dataclass(frozen=True)
class TriggerCoincidentPeriodicReport:
    trigger_ability_id: int
    periodic_ability_id: int
    tolerance_ms: float
    trigger_count: int
    coincident_trigger_count: int
    observations: tuple[TriggerCoincidentPeriodicObservation, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsTriggerCooccurrenceService:
    """Inspect periodic rows that occur at a reviewed trigger timestamp.

    This is observational evidence only. It exists to distinguish an actual
    trigger-time periodic occurrence from timestamp fan-out, duplicate rows, or a
    later recurring stream. The logs database is always opened read-only.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        trigger_ability_id: int,
        periodic_ability_id: int,
        tolerance_ms: float = 50.0,
        next_window_ms: float = 3000.0,
    ) -> TriggerCoincidentPeriodicReport:
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)
        trigger_id = int(trigger_ability_id)
        periodic_id = int(periodic_ability_id)
        tolerance = float(tolerance_ms)
        next_window = float(next_window_ms)
        if trigger_id <= 0 or periodic_id <= 0:
            return TriggerCoincidentPeriodicReport(
                trigger_id,
                periodic_id,
                tolerance,
                0,
                0,
                (),
                ("positive trigger and periodic ability IDs are required",),
            )
        if tolerance < 0 or next_window <= tolerance:
            return TriggerCoincidentPeriodicReport(
                trigger_id,
                periodic_id,
                tolerance,
                0,
                0,
                (),
                ("tolerance must be non-negative and next_window_ms must exceed tolerance",),
            )

        with self._open_logs() as db:
            required = {
                "report_code",
                "fight_id",
                "event_index",
                "timestamp",
                "source_id",
                "target_id",
                "ability_game_id",
                "hit_type",
                "amount",
                "tick",
                "cast_track_id",
            }
            columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()
            }
            missing = sorted(required - columns)
            if missing:
                return TriggerCoincidentPeriodicReport(
                    trigger_id,
                    periodic_id,
                    tolerance,
                    0,
                    0,
                    (),
                    ("log_event is missing required columns: " + ", ".join(missing),),
                )

            triggers = db.execute(
                """
                SELECT report_code,fight_id,event_index,timestamp,source_id,target_id,
                       hit_type,amount,tick,cast_track_id
                FROM log_event
                WHERE ability_game_id=?
                ORDER BY report_code,fight_id,source_id,timestamp,event_index
                """,
                (trigger_id,),
            ).fetchall()

            observations: list[TriggerCoincidentPeriodicObservation] = []
            coincident_triggers: set[tuple[str, int, int, int]] = set()
            for trigger in triggers:
                if trigger["source_id"] is None:
                    continue
                trigger_time = float(trigger["timestamp"])
                rows = db.execute(
                    """
                    SELECT report_code,fight_id,event_index,timestamp,source_id,target_id,
                           hit_type,amount,tick,cast_track_id
                    FROM log_event
                    WHERE report_code=? AND fight_id=? AND source_id=?
                      AND ability_game_id=? AND timestamp>=? AND timestamp<=?
                    ORDER BY timestamp,event_index
                    """,
                    (
                        str(trigger["report_code"]),
                        int(trigger["fight_id"]),
                        int(trigger["source_id"]),
                        periodic_id,
                        trigger_time - tolerance,
                        trigger_time + next_window,
                    ),
                ).fetchall()
                coincident = [
                    row for row in rows if abs(float(row["timestamp"]) - trigger_time) <= tolerance
                ]
                if not coincident:
                    continue
                key = (
                    str(trigger["report_code"]),
                    int(trigger["fight_id"]),
                    int(trigger["source_id"]),
                    int(trigger["event_index"]),
                )
                coincident_triggers.add(key)
                later = [row for row in rows if float(row["timestamp"]) > trigger_time + tolerance]
                next_row = later[0] if later else None
                for row in coincident:
                    observations.append(
                        TriggerCoincidentPeriodicObservation(
                            report_code=str(trigger["report_code"]),
                            fight_id=int(trigger["fight_id"]),
                            source_id=int(trigger["source_id"]),
                            trigger_event_index=int(trigger["event_index"]),
                            trigger_timestamp_ms=trigger_time,
                            trigger_target_id=self._optional_int(trigger["target_id"]),
                            trigger_hit_type=self._optional_text(trigger["hit_type"]),
                            trigger_amount=self._optional_float(trigger["amount"]),
                            trigger_cast_track_id=self._optional_int(trigger["cast_track_id"]),
                            periodic_event_index=int(row["event_index"]),
                            periodic_timestamp_ms=float(row["timestamp"]),
                            periodic_target_id=self._optional_int(row["target_id"]),
                            periodic_hit_type=self._optional_text(row["hit_type"]),
                            periodic_amount=self._optional_float(row["amount"]),
                            periodic_tick=self._optional_bool(row["tick"]),
                            periodic_cast_track_id=self._optional_int(row["cast_track_id"]),
                            next_periodic_event_index=(
                                int(next_row["event_index"]) if next_row is not None else None
                            ),
                            next_periodic_timestamp_ms=(
                                float(next_row["timestamp"]) if next_row is not None else None
                            ),
                            next_periodic_target_id=(
                                self._optional_int(next_row["target_id"])
                                if next_row is not None
                                else None
                            ),
                            next_periodic_hit_type=(
                                self._optional_text(next_row["hit_type"])
                                if next_row is not None
                                else None
                            ),
                            next_periodic_amount=(
                                self._optional_float(next_row["amount"])
                                if next_row is not None
                                else None
                            ),
                            next_periodic_tick=(
                                self._optional_bool(next_row["tick"])
                                if next_row is not None
                                else None
                            ),
                        )
                    )

        unresolved: list[str] = []
        if not triggers:
            unresolved.append(f"no trigger ability {trigger_id} observations found")
        if triggers and not observations:
            unresolved.append(
                f"no periodic ability {periodic_id} rows occurred within ±{tolerance:g}ms of trigger"
            )
        return TriggerCoincidentPeriodicReport(
            trigger_ability_id=trigger_id,
            periodic_ability_id=periodic_id,
            tolerance_ms=tolerance,
            trigger_count=len(triggers),
            coincident_trigger_count=len(coincident_triggers),
            observations=tuple(observations),
            unresolved=tuple(unresolved),
        )

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _optional_float(value: object) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @staticmethod
    def _optional_bool(value: object) -> bool | None:
        return None if value is None else bool(value)


__all__ = [
    "RotationDDPeriodicEsoLogsTriggerCooccurrenceService",
    "TriggerCoincidentPeriodicObservation",
    "TriggerCoincidentPeriodicReport",
]
