from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.rotation_unnerving_boneyard_refresh_boundary_evidence_service import (
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService,
)


@dataclass(frozen=True)
class RotationUnnervingBoneyardRefreshAnomaly:
    report_code: str
    fight_id: int
    source_id: int
    old_cast_track_id: int
    new_cast_track_id: int
    new_cast_timestamp_ms: float
    old_event_timestamp_ms: float
    old_event_index: int
    first_new_event_timestamp_ms: float
    first_new_event_index: int

    @property
    def old_event_after_new_cast_seconds(self) -> float:
        return (self.old_event_timestamp_ms - self.new_cast_timestamp_ms) / 1000.0

    @property
    def old_event_before_first_new_seconds(self) -> float:
        return (self.first_new_event_timestamp_ms - self.old_event_timestamp_ms) / 1000.0


@dataclass(frozen=True)
class RotationUnnervingBoneyardRefreshAnomalyReport:
    anomalies: tuple[RotationUnnervingBoneyardRefreshAnomaly, ...]
    unresolved: tuple[str, ...] = ()


class RotationUnnervingBoneyardRefreshAnomalyService(
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService
):
    """Drill into old-track 117809 events that occur after a replacement Boneyard cast.

    Research-only. Uses the same canonical cast identity rules as the summary boundary
    service and reports exact timestamps/event ordering without promoting semantics.
    """

    def inspect_anomalies(
        self,
        *,
        candidate_ability_id: int = 117809,
    ) -> RotationUnnervingBoneyardRefreshAnomalyReport:
        if not self.logs_database_path.is_file():
            return RotationUnnervingBoneyardRefreshAnomalyReport(
                (), (f"ESO Logs database not found: {self.logs_database_path}",)
            )

        aliases = self._cast_aliases()
        anomalies: list[RotationUnnervingBoneyardRefreshAnomaly] = []
        with self._open_logs() as db:
            error = self._schema_error(db)
            if error:
                return RotationUnnervingBoneyardRefreshAnomalyReport((), (error,))
            rows = db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event "
                "ORDER BY report_code,fight_id,source_id,timestamp,event_index"
            ).fetchall()

        casts: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        events_by_track: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["source_id"] is None:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
            event_type = str(row["event_type"] or "").casefold()
            if event_type in self._CAST_TYPES and self._matches_boneyard_cast(row, aliases=aliases):
                casts.setdefault(key, []).append(row)
            if (
                row["ability_game_id"] == int(candidate_ability_id)
                and row["cast_track_id"] is not None
                and event_type == "damage"
            ):
                events_by_track.setdefault((*key, int(row["cast_track_id"])), []).append(row)

        for key, group in casts.items():
            ordered = sorted(group, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            for old_cast, new_cast in zip(ordered, ordered[1:]):
                if old_cast["cast_track_id"] is None or new_cast["cast_track_id"] is None:
                    continue
                old_track = int(old_cast["cast_track_id"])
                new_track = int(new_cast["cast_track_id"])
                old_events = events_by_track.get((*key, old_track), ())
                new_events = events_by_track.get((*key, new_track), ())
                if not old_events or not new_events:
                    continue
                first_new = min(new_events, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
                new_cast_key = (float(new_cast["timestamp"]), int(new_cast["event_index"]))
                first_new_key = (float(first_new["timestamp"]), int(first_new["event_index"]))
                for old_event in old_events:
                    old_key = (float(old_event["timestamp"]), int(old_event["event_index"]))
                    if new_cast_key < old_key < first_new_key:
                        anomalies.append(
                            RotationUnnervingBoneyardRefreshAnomaly(
                                report_code=key[0],
                                fight_id=key[1],
                                source_id=key[2],
                                old_cast_track_id=old_track,
                                new_cast_track_id=new_track,
                                new_cast_timestamp_ms=float(new_cast["timestamp"]),
                                old_event_timestamp_ms=float(old_event["timestamp"]),
                                old_event_index=int(old_event["event_index"]),
                                first_new_event_timestamp_ms=float(first_new["timestamp"]),
                                first_new_event_index=int(first_new["event_index"]),
                            )
                        )

        unresolved = () if anomalies else (
            "no old-track 117809 event was observed between a new Boneyard cast and its first new-track event",
        )
        return RotationUnnervingBoneyardRefreshAnomalyReport(tuple(anomalies), unresolved)


__all__ = [
    "RotationUnnervingBoneyardRefreshAnomaly",
    "RotationUnnervingBoneyardRefreshAnomalyReport",
    "RotationUnnervingBoneyardRefreshAnomalyService",
]
