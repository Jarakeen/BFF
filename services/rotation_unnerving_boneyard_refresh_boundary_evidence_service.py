from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median


@dataclass(frozen=True)
class RotationUnnervingBoneyardRefreshBoundaryReport:
    consecutive_pairs: int
    comparable_pairs: int
    pairs_with_old_event_after_new_cast: int
    pairs_with_old_event_at_new_cast: int
    pairs_with_old_event_at_or_after_first_new_event: int
    exact_timestamp_old_events_at_new_cast: int
    median_last_old_before_new_cast_seconds: float | None
    median_first_new_after_new_cast_seconds: float | None
    unresolved: tuple[str, ...] = ()


class RotationUnnervingBoneyardRefreshBoundaryEvidenceService:
    """Review 117809 old-track survival across consecutive Boneyard casts.

    Research-only. This service distinguishes cast-time replacement evidence from the
    weaker first-new-event boundary. It never promotes executable semantics itself.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(self, *, candidate_ability_id: int = 117809) -> RotationUnnervingBoneyardRefreshBoundaryReport:
        if not self.logs_database_path.is_file():
            return RotationUnnervingBoneyardRefreshBoundaryReport(
                0, 0, 0, 0, 0, 0, None, None,
                (f"ESO Logs database not found: {self.logs_database_path}",),
            )

        with self._open_logs() as db:
            error = self._schema_error(db)
            if error:
                return RotationUnnervingBoneyardRefreshBoundaryReport(
                    0, 0, 0, 0, 0, 0, None, None, (error,),
                )
            rows = db.execute(
                "SELECT report_code, fight_id, event_index, timestamp, event_type, source_id, "
                "ability_game_id, cast_track_id, raw_json FROM log_event "
                "ORDER BY report_code, fight_id, source_id, timestamp, event_index"
            ).fetchall()

        casts: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        candidate_by_track: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["source_id"] is None:
                continue
            report = str(row["report_code"])
            fight = int(row["fight_id"])
            source = int(row["source_id"])
            event_type = str(row["event_type"] or "").casefold()
            if event_type in {"cast", "begincast", "completecast"} and self._ability_name(row["raw_json"]) == "Unnerving Boneyard":
                casts.setdefault((report, fight, source), []).append(row)
            if (
                row["ability_game_id"] == candidate_ability_id
                and row["cast_track_id"] is not None
                and event_type == "damage"
            ):
                candidate_by_track.setdefault(
                    (report, fight, source, int(row["cast_track_id"])), []
                ).append(row)

        consecutive_pairs = 0
        comparable_pairs = 0
        after_new_cast = 0
        at_new_cast = 0
        at_or_after_first_new = 0
        exact_at_new_cast = 0
        last_old_before_offsets: list[float] = []
        first_new_offsets: list[float] = []

        for key, cast_rows in casts.items():
            ordered = sorted(cast_rows, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            for old_cast, new_cast in zip(ordered, ordered[1:]):
                consecutive_pairs += 1
                if old_cast["cast_track_id"] is None or new_cast["cast_track_id"] is None:
                    continue
                old_events = candidate_by_track.get((*key, int(old_cast["cast_track_id"])), [])
                new_events = candidate_by_track.get((*key, int(new_cast["cast_track_id"])), [])
                if not old_events or not new_events:
                    continue
                comparable_pairs += 1
                new_cast_key = (float(new_cast["timestamp"]), int(new_cast["event_index"]))
                first_new = min(new_events, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
                first_new_key = (float(first_new["timestamp"]), int(first_new["event_index"]))
                first_new_offsets.append((float(first_new["timestamp"]) - float(new_cast["timestamp"])) / 1000.0)

                old_after_cast = [
                    row for row in old_events
                    if (float(row["timestamp"]), int(row["event_index"])) > new_cast_key
                ]
                old_at_cast = [row for row in old_events if float(row["timestamp"]) == float(new_cast["timestamp"])]
                old_at_or_after_first = [
                    row for row in old_events
                    if (float(row["timestamp"]), int(row["event_index"])) >= first_new_key
                ]
                if old_after_cast:
                    after_new_cast += 1
                if old_at_cast:
                    at_new_cast += 1
                    exact_at_new_cast += len(old_at_cast)
                if old_at_or_after_first:
                    at_or_after_first_new += 1

                before_cast = [
                    row for row in old_events
                    if (float(row["timestamp"]), int(row["event_index"])) < new_cast_key
                ]
                if before_cast:
                    last_old = max(before_cast, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
                    last_old_before_offsets.append(
                        (float(new_cast["timestamp"]) - float(last_old["timestamp"])) / 1000.0
                    )

        unresolved: list[str] = []
        if comparable_pairs == 0:
            unresolved.append("no consecutive Boneyard cast pairs had 117809 evidence on both cast tracks")

        return RotationUnnervingBoneyardRefreshBoundaryReport(
            consecutive_pairs=consecutive_pairs,
            comparable_pairs=comparable_pairs,
            pairs_with_old_event_after_new_cast=after_new_cast,
            pairs_with_old_event_at_new_cast=at_new_cast,
            pairs_with_old_event_at_or_after_first_new_event=at_or_after_first_new,
            exact_timestamp_old_events_at_new_cast=exact_at_new_cast,
            median_last_old_before_new_cast_seconds=(
                float(median(last_old_before_offsets)) if last_old_before_offsets else None
            ),
            median_first_new_after_new_cast_seconds=(
                float(median(first_new_offsets)) if first_new_offsets else None
            ),
            unresolved=tuple(unresolved),
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
            "source_id", "ability_game_id", "cast_track_id", "raw_json",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None

    @staticmethod
    def _ability_name(raw_json: object) -> str | None:
        if not raw_json:
            return None
        try:
            payload = json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        ability = payload.get("ability") if isinstance(payload, dict) else None
        if not isinstance(ability, dict):
            return None
        value = ability.get("name")
        text = str(value).strip() if value is not None else ""
        return text or None


__all__ = [
    "RotationUnnervingBoneyardRefreshBoundaryEvidenceService",
    "RotationUnnervingBoneyardRefreshBoundaryReport",
]
