from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median


_CAST_TYPES = {"begincast", "cast", "completecast"}


@dataclass(frozen=True)
class RotationMeteorCandidateNearbyCast:
    ability_game_id: int | None
    ability_name: str | None
    event_type: str
    offset_seconds: float
    cast_track_id: int | None
    shares_damage_cast_track: bool


@dataclass(frozen=True)
class RotationMeteorCandidateRun:
    report_code: str
    fight_id: int
    source_id: int
    start_timestamp: float
    end_timestamp: float
    damage_event_count: int
    distinct_target_count: int
    median_interval_seconds: float | None
    cast_track_ids: tuple[int, ...]
    nearby_casts: tuple[RotationMeteorCandidateNearbyCast, ...]


@dataclass(frozen=True)
class RotationMeteorCandidateDrilldown:
    ability_game_id: int
    ability_names: tuple[str, ...]
    damage_event_count: int
    run_count: int
    source_actor_count: int
    median_run_span_seconds: float | None
    median_run_interval_seconds: float | None
    runs_with_prior_cast: int
    runs_with_same_track_prior_cast: int
    nearest_prior_cast_id_counts: tuple[tuple[int | None, int], ...]
    nearest_prior_cast_name_counts: tuple[tuple[str, int], ...]
    runs: tuple[RotationMeteorCandidateRun, ...]


@dataclass(frozen=True)
class RotationMeteorCandidateDrilldownReport:
    candidates: tuple[RotationMeteorCandidateDrilldown, ...]
    unresolved: tuple[str, ...] = ()


class RotationMeteorEsoLogsCandidateDrilldownService:
    """Inspect anonymous Meteor-like candidates for cast/run topology.

    Research-only. Candidate ids remain observational ESO Logs handles. The service
    segments damage into runs, then inspects nearby prior cast-like events from the
    same report/fight/source. It never identifies or promotes a candidate as Meteor.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        ability_ids: tuple[int, ...],
        run_gap_seconds: float = 2.25,
        prior_cast_window_seconds: float = 6.0,
        nearby_cast_limit: int = 5,
    ) -> RotationMeteorCandidateDrilldownReport:
        ids = tuple(dict.fromkeys(int(value) for value in ability_ids))
        if not ids:
            return RotationMeteorCandidateDrilldownReport((), ("at least one candidate ability id is required",))
        if not self.logs_database_path.is_file():
            return RotationMeteorCandidateDrilldownReport(
                (), (f"ESO Logs database not found: {self.logs_database_path}",)
            )

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return RotationMeteorCandidateDrilldownReport((), (schema_error,))
            placeholders = ",".join("?" for _ in ids)
            damage_rows = db.execute(
                "SELECT report_code, fight_id, event_index, timestamp, source_id, target_id, "
                "ability_game_id, cast_track_id, raw_json FROM log_event "
                f"WHERE lower(event_type)='damage' AND ability_game_id IN ({placeholders}) "
                "ORDER BY report_code, fight_id, source_id, ability_game_id, timestamp, event_index",
                ids,
            ).fetchall()
            cast_rows = db.execute(
                "SELECT report_code, fight_id, event_index, timestamp, event_type, source_id, "
                "ability_game_id, cast_track_id, raw_json FROM log_event "
                "WHERE lower(event_type) IN ('begincast','cast','completecast') "
                "ORDER BY report_code, fight_id, source_id, timestamp, event_index"
            ).fetchall()

        casts_by_scope: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for row in cast_rows:
            if row["source_id"] is None:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
            casts_by_scope.setdefault(key, []).append(row)

        grouped: dict[tuple[int, str, int, int], list[sqlite3.Row]] = {}
        for row in damage_rows:
            if row["source_id"] is None or row["ability_game_id"] is None:
                continue
            key = (
                int(row["ability_game_id"]),
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
            )
            grouped.setdefault(key, []).append(row)

        by_ability_runs: dict[int, list[RotationMeteorCandidateRun]] = {ability_id: [] for ability_id in ids}
        by_ability_names: dict[int, set[str]] = {ability_id: set() for ability_id in ids}
        by_ability_sources: dict[int, set[int]] = {ability_id: set() for ability_id in ids}
        by_ability_events: dict[int, int] = {ability_id: 0 for ability_id in ids}

        for (ability_id, report_code, fight_id, source_id), rows in grouped.items():
            by_ability_sources[ability_id].add(source_id)
            by_ability_events[ability_id] += len(rows)
            for row in rows:
                name = self._ability_name(row["raw_json"])
                if name:
                    by_ability_names[ability_id].add(name)
            for run_rows in self._split_runs(rows, run_gap_seconds=run_gap_seconds):
                run = self._build_run(
                    run_rows,
                    casts_by_scope.get((report_code, fight_id, source_id), ()),
                    report_code=report_code,
                    fight_id=fight_id,
                    source_id=source_id,
                    prior_cast_window_seconds=prior_cast_window_seconds,
                    nearby_cast_limit=nearby_cast_limit,
                )
                by_ability_runs[ability_id].append(run)

        candidates: list[RotationMeteorCandidateDrilldown] = []
        unresolved: list[str] = []
        for ability_id in ids:
            runs = tuple(sorted(by_ability_runs[ability_id], key=lambda item: (item.report_code, item.fight_id, item.start_timestamp)))
            if not runs:
                unresolved.append(f"candidate {ability_id}: no damage rows found")
                continue
            spans = [(run.end_timestamp - run.start_timestamp) / 1000.0 for run in runs]
            intervals = [run.median_interval_seconds for run in runs if run.median_interval_seconds is not None]
            nearest_ids: dict[int | None, int] = {}
            nearest_names: dict[str, int] = {}
            runs_with_prior = 0
            runs_with_same_track = 0
            for run in runs:
                if not run.nearby_casts:
                    continue
                runs_with_prior += 1
                nearest = run.nearby_casts[0]
                nearest_ids[nearest.ability_game_id] = nearest_ids.get(nearest.ability_game_id, 0) + 1
                name_key = nearest.ability_name or "(unnamed)"
                nearest_names[name_key] = nearest_names.get(name_key, 0) + 1
                if any(cast.shares_damage_cast_track for cast in run.nearby_casts):
                    runs_with_same_track += 1
            candidates.append(
                RotationMeteorCandidateDrilldown(
                    ability_game_id=ability_id,
                    ability_names=tuple(sorted(by_ability_names[ability_id], key=str.casefold)),
                    damage_event_count=by_ability_events[ability_id],
                    run_count=len(runs),
                    source_actor_count=len(by_ability_sources[ability_id]),
                    median_run_span_seconds=float(median(spans)) if spans else None,
                    median_run_interval_seconds=float(median(intervals)) if intervals else None,
                    runs_with_prior_cast=runs_with_prior,
                    runs_with_same_track_prior_cast=runs_with_same_track,
                    nearest_prior_cast_id_counts=tuple(sorted(nearest_ids.items(), key=lambda item: (-item[1], item[0] if item[0] is not None else -1))),
                    nearest_prior_cast_name_counts=tuple(sorted(nearest_names.items(), key=lambda item: (-item[1], item[0].casefold()))),
                    runs=runs,
                )
            )
        return RotationMeteorCandidateDrilldownReport(tuple(candidates), tuple(unresolved))

    @staticmethod
    def _split_runs(rows: list[sqlite3.Row], *, run_gap_seconds: float) -> tuple[tuple[sqlite3.Row, ...], ...]:
        if not rows:
            return ()
        ordered = sorted(rows, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
        runs: list[list[sqlite3.Row]] = [[ordered[0]]]
        for row in ordered[1:]:
            gap = (float(row["timestamp"]) - float(runs[-1][-1]["timestamp"])) / 1000.0
            if gap > run_gap_seconds:
                runs.append([row])
            else:
                runs[-1].append(row)
        return tuple(tuple(run) for run in runs)

    def _build_run(
        self,
        rows: tuple[sqlite3.Row, ...],
        cast_rows: tuple[sqlite3.Row, ...] | list[sqlite3.Row],
        *,
        report_code: str,
        fight_id: int,
        source_id: int,
        prior_cast_window_seconds: float,
        nearby_cast_limit: int,
    ) -> RotationMeteorCandidateRun:
        start = float(rows[0]["timestamp"])
        end = float(rows[-1]["timestamp"])
        unique_times = sorted({float(row["timestamp"]) for row in rows})
        intervals = [(b - a) / 1000.0 for a, b in zip(unique_times, unique_times[1:])]
        targets = {int(row["target_id"]) for row in rows if row["target_id"] is not None}
        track_ids = tuple(sorted({int(row["cast_track_id"]) for row in rows if row["cast_track_id"] is not None}))
        nearby: list[RotationMeteorCandidateNearbyCast] = []
        for cast in reversed(cast_rows):
            cast_time = float(cast["timestamp"])
            if cast_time > start:
                continue
            offset = (start - cast_time) / 1000.0
            if offset > prior_cast_window_seconds:
                break
            cast_track = int(cast["cast_track_id"]) if cast["cast_track_id"] is not None else None
            nearby.append(
                RotationMeteorCandidateNearbyCast(
                    ability_game_id=int(cast["ability_game_id"]) if cast["ability_game_id"] is not None else None,
                    ability_name=self._ability_name(cast["raw_json"]),
                    event_type=str(cast["event_type"] or "").strip().casefold(),
                    offset_seconds=offset,
                    cast_track_id=cast_track,
                    shares_damage_cast_track=cast_track is not None and cast_track in track_ids,
                )
            )
            if len(nearby) >= nearby_cast_limit:
                break
        return RotationMeteorCandidateRun(
            report_code=report_code,
            fight_id=fight_id,
            source_id=source_id,
            start_timestamp=start,
            end_timestamp=end,
            damage_event_count=len(rows),
            distinct_target_count=len(targets),
            median_interval_seconds=float(median(intervals)) if intervals else None,
            cast_track_ids=track_ids,
            nearby_casts=tuple(nearby),
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
        required = {"report_code", "fight_id", "event_index", "timestamp", "event_type", "source_id", "target_id", "ability_game_id", "cast_track_id", "raw_json"}
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
