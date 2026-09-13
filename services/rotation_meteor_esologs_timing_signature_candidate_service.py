from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median


@dataclass(frozen=True)
class RotationMeteorTimingSignatureCandidate:
    ability_game_id: int
    ability_names: tuple[str, ...]
    source_actor_count: int
    event_count: int
    occurrence_count: int
    median_interval_seconds: float | None
    one_second_interval_matches: int
    median_run_span_seconds: float | None
    maximum_run_span_seconds: float | None


@dataclass(frozen=True)
class RotationMeteorTimingSignatureCandidateReport:
    candidates: tuple[RotationMeteorTimingSignatureCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationMeteorEsoLogsTimingSignatureCandidateService:
    """Find anonymous damage streams that resemble Meteor's reviewed 11s / 1s DoT shape.

    Research-only. This service does not identify an ability as Meteor and never promotes
    numeric ids into runtime semantics. It exists only to determine whether the imported
    ESO Logs corpus contains plausible candidates worth manual review.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        interval_seconds: float = 1.0,
        interval_tolerance_seconds: float = 0.15,
        maximum_run_span_seconds: float = 11.5,
        minimum_occurrences: int = 4,
        minimum_interval_matches: int = 3,
    ) -> RotationMeteorTimingSignatureCandidateReport:
        if not self.logs_database_path.is_file():
            return RotationMeteorTimingSignatureCandidateReport(
                candidates=(),
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",),
            )

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return RotationMeteorTimingSignatureCandidateReport(candidates=(), unresolved=(schema_error,))
            rows = db.execute(
                "SELECT report_code, fight_id, timestamp, source_id, ability_game_id, raw_json "
                "FROM log_event WHERE lower(event_type)='damage' AND ability_game_id IS NOT NULL "
                "ORDER BY report_code, fight_id, source_id, ability_game_id, timestamp, event_index"
            ).fetchall()

        groups: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["source_id"] is None:
                continue
            key = (
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
                int(row["ability_game_id"]),
            )
            groups.setdefault(key, []).append(row)

        buckets: dict[int, dict[str, object]] = {}
        for (_report, _fight, source_id, ability_id), event_rows in groups.items():
            times = sorted({float(row["timestamp"]) for row in event_rows})
            if len(times) < minimum_occurrences:
                continue
            intervals = [(b - a) / 1000.0 for a, b in zip(times, times[1:])]
            matches = sum(1 for value in intervals if abs(value - interval_seconds) <= interval_tolerance_seconds)
            if matches < minimum_interval_matches:
                continue
            span = (times[-1] - times[0]) / 1000.0
            if span > maximum_run_span_seconds:
                continue

            bucket = buckets.setdefault(
                ability_id,
                {
                    "names": set(),
                    "sources": set(),
                    "events": 0,
                    "occurrences": 0,
                    "intervals": [],
                    "matches": 0,
                    "spans": [],
                },
            )
            bucket["sources"].add(source_id)
            bucket["events"] = int(bucket["events"]) + len(event_rows)
            bucket["occurrences"] = int(bucket["occurrences"]) + len(times)
            bucket["intervals"].extend(intervals)
            bucket["matches"] = int(bucket["matches"]) + matches
            bucket["spans"].append(span)
            for row in event_rows:
                name = self._ability_name(row["raw_json"])
                if name:
                    bucket["names"].add(name)

        candidates = [
            RotationMeteorTimingSignatureCandidate(
                ability_game_id=ability_id,
                ability_names=tuple(sorted(data["names"], key=str.casefold)),
                source_actor_count=len(data["sources"]),
                event_count=int(data["events"]),
                occurrence_count=int(data["occurrences"]),
                median_interval_seconds=(float(median(data["intervals"])) if data["intervals"] else None),
                one_second_interval_matches=int(data["matches"]),
                median_run_span_seconds=(float(median(data["spans"])) if data["spans"] else None),
                maximum_run_span_seconds=(max(float(value) for value in data["spans"]) if data["spans"] else None),
            )
            for ability_id, data in buckets.items()
        ]
        candidates.sort(
            key=lambda item: (
                -item.one_second_interval_matches,
                -item.occurrence_count,
                item.ability_game_id,
            )
        )
        unresolved = () if candidates else (
            "no anonymous damage stream matched the reviewed Meteor-like 11s / 1s timing filter",
        )
        return RotationMeteorTimingSignatureCandidateReport(tuple(candidates), unresolved)

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
        required = {"report_code", "fight_id", "event_index", "timestamp", "event_type", "source_id", "ability_game_id", "raw_json"}
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
