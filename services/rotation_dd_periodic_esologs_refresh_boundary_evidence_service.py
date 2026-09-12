from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsRefreshBoundaryObservation:
    report_code: str
    fight_id: int
    source_id: int
    old_cast_track_id: int | None
    new_cast_track_id: int | None
    old_impact_timestamp_ms: float
    new_impact_timestamp_ms: float
    old_periodic_before_boundary: int
    old_periodic_at_boundary: int
    old_periodic_after_boundary: int
    last_old_periodic_offset_seconds: float | None
    first_new_periodic_offset_seconds: float | None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport:
    skill_entity_id: str
    impact_ability_id: int
    periodic_ability_id: int
    boundary_tolerance_ms: float
    observations: tuple[RotationDDPeriodicEsoLogsRefreshBoundaryObservation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def old_tick_at_boundary_count(self) -> int:
        return sum(item.old_periodic_at_boundary for item in self.observations)

    @property
    def old_tick_after_boundary_count(self) -> int:
        return sum(item.old_periodic_after_boundary for item in self.observations)

    @property
    def observations_with_old_periodic(self) -> int:
        return sum(
            1
            for item in self.observations
            if (
                item.old_periodic_before_boundary
                + item.old_periodic_at_boundary
                + item.old_periodic_after_boundary
            )
            > 0
        )

    @property
    def median_last_old_periodic_offset_seconds(self) -> float | None:
        values = tuple(
            item.last_old_periodic_offset_seconds
            for item in self.observations
            if item.last_old_periodic_offset_seconds is not None
        )
        return float(median(values)) if values else None


class RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService:
    """Observe old periodic-instance behavior around the next reviewed impact.

    Canonical lower-snake identity selects the cast skill. Numeric impact/periodic
    IDs are evidence handles only. The service relies on ESO Logs cast-track IDs when
    available so old-instance periodic events can be distinguished from the new
    instance after replacement. Results remain observational and are never promoted
    into executable refresh semantics automatically.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
    ) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)

    def inspect(
        self,
        skill_entity_id: str,
        *,
        impact_ability_id: int,
        periodic_ability_id: int,
        active_window_seconds: float,
        boundary_tolerance_ms: float = 50.0,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport:
        identity = ability_entity_id(skill_entity_id)
        unresolved: list[str] = []
        if not identity:
            return self._report(
                "",
                impact_ability_id,
                periodic_ability_id,
                boundary_tolerance_ms,
                unresolved=("canonical skill identity is required",),
            )
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)
        if int(impact_ability_id) <= 0 or int(periodic_ability_id) <= 0:
            return self._report(
                identity,
                impact_ability_id,
                periodic_ability_id,
                boundary_tolerance_ms,
                unresolved=("positive observational impact and periodic ability IDs are required",),
            )
        if float(active_window_seconds) <= 0:
            return self._report(
                identity,
                impact_ability_id,
                periodic_ability_id,
                boundary_tolerance_ms,
                unresolved=("active_window_seconds must be positive",),
            )
        tolerance = float(boundary_tolerance_ms)
        if tolerance < 0:
            return self._report(
                identity,
                impact_ability_id,
                periodic_ability_id,
                boundary_tolerance_ms,
                unresolved=("boundary_tolerance_ms must be non-negative",),
            )

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        if resolution.rank is not None:
            aliases.update(
                self._numeric_aliases(
                    resolution.rank.skill_id,
                    resolution.rank.morph,
                    resolution.rank.base_ability_id,
                )
            )
        elif resolution.unresolved:
            unresolved.extend(
                str(item).strip() for item in resolution.unresolved if str(item).strip()
            )

        observations: list[RotationDDPeriodicEsoLogsRefreshBoundaryObservation] = []
        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(
                    identity,
                    impact_ability_id,
                    periodic_ability_id,
                    tolerance,
                    unresolved=tuple(dict.fromkeys((*unresolved, schema_error))),
                )
            casts = tuple(
                row
                for row in self._cast_rows(
                    db,
                    report_code=report_code,
                    fight_id=fight_id,
                    source_id=source_id,
                )
                if self._matches_cast_identity(row, identity=identity, aliases=aliases)
            )
            if not casts:
                unresolved.append(f"{identity}: no matching cast observations found")
                return self._report(
                    identity,
                    impact_ability_id,
                    periodic_ability_id,
                    tolerance,
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            anchor_type = next(
                kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts)
            )
            grouped: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
            for row in casts:
                if self._event_type(row) != anchor_type or row["source_id"] is None:
                    continue
                key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
                grouped.setdefault(key, []).append(row)

            for (group_report, group_fight, group_source), group_casts in grouped.items():
                group_casts.sort(key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
                events = self._effect_rows(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    impact_ability_id=int(impact_ability_id),
                    periodic_ability_id=int(periodic_ability_id),
                )
                impact_by_track = self._first_event_by_track(events, int(impact_ability_id))
                periodic_by_track = self._events_by_track(events, int(periodic_ability_id))

                for old_cast, new_cast in zip(group_casts, group_casts[1:]):
                    old_track = self._track(old_cast)
                    new_track = self._track(new_cast)
                    if old_track is None or new_track is None:
                        continue
                    old_impact = impact_by_track.get(old_track)
                    new_impact = impact_by_track.get(new_track)
                    if old_impact is None or new_impact is None:
                        continue
                    old_impact_time = float(old_impact["timestamp"])
                    new_impact_time = float(new_impact["timestamp"])
                    if new_impact_time <= old_impact_time:
                        continue
                    if new_impact_time - old_impact_time > float(active_window_seconds) * 1000.0:
                        continue

                    old_periodic = tuple(
                        row
                        for row in periodic_by_track.get(old_track, ())
                        if old_impact_time <= float(row["timestamp"])
                        <= new_impact_time + max(tolerance, 250.0)
                    )
                    new_periodic = tuple(
                        row
                        for row in periodic_by_track.get(new_track, ())
                        if float(row["timestamp"]) >= new_impact_time
                    )

                    before = tuple(
                        row
                        for row in old_periodic
                        if float(row["timestamp"]) < new_impact_time - tolerance
                    )
                    at_boundary = tuple(
                        row
                        for row in old_periodic
                        if abs(float(row["timestamp"]) - new_impact_time) <= tolerance
                    )
                    after = tuple(
                        row
                        for row in old_periodic
                        if float(row["timestamp"]) > new_impact_time + tolerance
                    )
                    last_old = max(
                        (float(row["timestamp"]) for row in old_periodic),
                        default=None,
                    )
                    first_new = min(
                        (float(row["timestamp"]) for row in new_periodic),
                        default=None,
                    )
                    observations.append(
                        RotationDDPeriodicEsoLogsRefreshBoundaryObservation(
                            report_code=group_report,
                            fight_id=group_fight,
                            source_id=group_source,
                            old_cast_track_id=old_track,
                            new_cast_track_id=new_track,
                            old_impact_timestamp_ms=old_impact_time,
                            new_impact_timestamp_ms=new_impact_time,
                            old_periodic_before_boundary=len(before),
                            old_periodic_at_boundary=len(at_boundary),
                            old_periodic_after_boundary=len(after),
                            last_old_periodic_offset_seconds=(
                                None
                                if last_old is None
                                else (last_old - new_impact_time) / 1000.0
                            ),
                            first_new_periodic_offset_seconds=(
                                None
                                if first_new is None
                                else (first_new - new_impact_time) / 1000.0
                            ),
                        )
                    )

        if not observations:
            unresolved.append(
                f"{identity}: no consecutive cast pairs with cast-track-linked impact evidence were observed"
            )
        return self._report(
            identity,
            impact_ability_id,
            periodic_ability_id,
            tolerance,
            observations=tuple(observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int, base_ability_id: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            aliases = {int(base_ability_id)} if int(base_ability_id) > 0 else set()
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_rank'"
            ).fetchone()
            if table is not None:
                aliases.update(
                    int(row["ability_id"])
                    for row in db.execute(
                        "SELECT ability_id FROM skill_rank WHERE skill_id=? "
                        "AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
                        (int(skill_id), int(morph)),
                    ).fetchall()
                )
            return tuple(sorted(value for value in aliases if value > 0))

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        row = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'").fetchone()
        if row is None:
            return "log_event table is unavailable"
        required = {
            "report_code", "fight_id", "event_index", "timestamp", "event_type",
            "source_id", "ability_game_id", "cast_track_id", "raw_json",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None

    @staticmethod
    def _cast_rows(
        db: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        clauses = ["lower(event_type) IN ('cast','begincast','completecast')"]
        params: list[object] = []
        if report_code is not None:
            clauses.append("report_code=?")
            params.append(str(report_code))
        if fight_id is not None:
            clauses.append("fight_id=?")
            params.append(int(fight_id))
        if source_id is not None:
            clauses.append("source_id=?")
            params.append(int(source_id))
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()
        )

    @staticmethod
    def _effect_rows(
        db: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        source_id: int,
        impact_ability_id: int,
        periodic_ability_id: int,
    ) -> tuple[sqlite3.Row, ...]:
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event "
                "WHERE report_code=? AND fight_id=? AND source_id=? "
                "AND ability_game_id IN (?,?) ORDER BY timestamp,event_index",
                (
                    report_code,
                    int(fight_id),
                    int(source_id),
                    int(impact_ability_id),
                    int(periodic_ability_id),
                ),
            ).fetchall()
        )

    @classmethod
    def _matches_cast_identity(cls, row: sqlite3.Row, *, identity: str, aliases: set[int]) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _track(row: sqlite3.Row) -> int | None:
        return int(row["cast_track_id"]) if row["cast_track_id"] is not None else None

    @classmethod
    def _first_event_by_track(
        cls,
        rows: tuple[sqlite3.Row, ...],
        ability_id: int,
    ) -> dict[int, sqlite3.Row]:
        result: dict[int, sqlite3.Row] = {}
        for row in rows:
            if row["ability_game_id"] is None or int(row["ability_game_id"]) != ability_id:
                continue
            track = cls._track(row)
            if track is None:
                continue
            current = result.get(track)
            if current is None or (float(row["timestamp"]), int(row["event_index"])) < (
                float(current["timestamp"]), int(current["event_index"])
            ):
                result[track] = row
        return result

    @classmethod
    def _events_by_track(
        cls,
        rows: tuple[sqlite3.Row, ...],
        ability_id: int,
    ) -> dict[int, tuple[sqlite3.Row, ...]]:
        grouped: dict[int, list[sqlite3.Row]] = {}
        for row in rows:
            if row["ability_game_id"] is None or int(row["ability_game_id"]) != ability_id:
                continue
            track = cls._track(row)
            if track is None:
                continue
            grouped.setdefault(track, []).append(row)
        return {
            track: tuple(sorted(items, key=lambda row: (float(row["timestamp"]), int(row["event_index"]))))
            for track, items in grouped.items()
        }

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().lower()

    @staticmethod
    def _ability_name_from_raw(raw_json: object) -> str | None:
        if raw_json is None:
            return None
        try:
            raw = json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        ability = raw.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        value = raw.get("abilityName")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _report(
        skill_entity_id: str,
        impact_ability_id: int,
        periodic_ability_id: int,
        boundary_tolerance_ms: float,
        *,
        observations: tuple[RotationDDPeriodicEsoLogsRefreshBoundaryObservation, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport:
        return RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport(
            skill_entity_id=skill_entity_id,
            impact_ability_id=int(impact_ability_id),
            periodic_ability_id=int(periodic_ability_id),
            boundary_tolerance_ms=float(boundary_tolerance_ms),
            observations=observations,
            unresolved=unresolved,
        )


__all__ = [
    "RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport",
    "RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService",
    "RotationDDPeriodicEsoLogsRefreshBoundaryObservation",
]
