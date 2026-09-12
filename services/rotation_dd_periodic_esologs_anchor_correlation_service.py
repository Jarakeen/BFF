from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsAnchorCorrelationReport:
    skill_entity_id: str
    impact_ability_id: int
    periodic_ability_id: int
    cast_count: int
    impact_observation_count: int
    periodic_observation_count: int
    cast_track_linked_impact_count: int
    cast_track_linked_periodic_count: int
    cast_to_impact_seconds: tuple[float, ...]
    impact_to_first_periodic_seconds: tuple[float, ...]
    periodic_intervals_seconds: tuple[float, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def median_cast_to_impact_seconds(self) -> float | None:
        return (
            float(median(self.cast_to_impact_seconds))
            if self.cast_to_impact_seconds
            else None
        )

    @property
    def median_impact_to_first_periodic_seconds(self) -> float | None:
        return (
            float(median(self.impact_to_first_periodic_seconds))
            if self.impact_to_first_periodic_seconds
            else None
        )


class RotationDDPeriodicEsoLogsAnchorCorrelationService:
    """Correlate a reviewed cast with observational impact and periodic effect IDs.

    Numeric IDs are evidence handles only. Canonical lower-snake skill identity
    remains authoritative for the cast. The supplied impact/periodic IDs are never
    promoted into canonical identity or executable semantics by this service.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _OCCURRENCE_CLUSTER_MS = 50.0

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
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsAnchorCorrelationReport:
        identity = ability_entity_id(skill_entity_id)
        unresolved: list[str] = []
        if not identity:
            return self._report(
                "",
                impact_ability_id=impact_ability_id,
                periodic_ability_id=periodic_ability_id,
                unresolved=("canonical skill identity is required",),
            )
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)
        if int(impact_ability_id) <= 0 or int(periodic_ability_id) <= 0:
            return self._report(
                identity,
                impact_ability_id=impact_ability_id,
                periodic_ability_id=periodic_ability_id,
                unresolved=("positive observational impact and periodic ability IDs are required",),
            )
        window_seconds = float(active_window_seconds)
        if window_seconds <= 0:
            return self._report(
                identity,
                impact_ability_id=impact_ability_id,
                periodic_ability_id=periodic_ability_id,
                unresolved=("active_window_seconds must be positive",),
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
                str(value).strip()
                for value in resolution.unresolved
                if str(value).strip()
            )

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(
                    identity,
                    impact_ability_id=impact_ability_id,
                    periodic_ability_id=periodic_ability_id,
                    unresolved=tuple(dict.fromkeys((*unresolved, schema_error))),
                )
            cast_rows = self._cast_rows(
                db,
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
            )
            casts = tuple(
                row
                for row in cast_rows
                if self._matches_cast_identity(row, identity=identity, aliases=aliases)
            )
            if not casts:
                unresolved.append(f"{identity}: no matching cast observations found")
                return self._report(
                    identity,
                    impact_ability_id=impact_ability_id,
                    periodic_ability_id=periodic_ability_id,
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            anchor_type = next(
                kind
                for kind in self._CAST_TYPES
                if any(self._event_type(row) == kind for row in casts)
            )
            anchors = tuple(row for row in casts if self._event_type(row) == anchor_type)
            groups: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
            for row in anchors:
                if row["source_id"] is None:
                    continue
                key = (
                    str(row["report_code"]),
                    int(row["fight_id"]),
                    int(row["source_id"]),
                )
                groups.setdefault(key, []).append(row)

            cast_to_impact: list[float] = []
            impact_to_periodic: list[float] = []
            periodic_intervals: list[float] = []
            impact_observations = 0
            periodic_observations = 0
            linked_impacts = 0
            linked_periodics = 0
            cast_count = 0

            for (group_report, group_fight, group_source), group_casts in groups.items():
                group_casts.sort(
                    key=lambda row: (float(row["timestamp"]), int(row["event_index"]))
                )
                events = self._effect_rows(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    ability_ids=(int(impact_ability_id), int(periodic_ability_id)),
                )
                for index, cast in enumerate(group_casts):
                    cast_count += 1
                    cast_time = float(cast["timestamp"])
                    next_cast = (
                        float(group_casts[index + 1]["timestamp"])
                        if index + 1 < len(group_casts)
                        else None
                    )
                    window_end = cast_time + window_seconds * 1000.0
                    if next_cast is not None:
                        window_end = min(window_end, next_cast)
                    cast_track = (
                        int(cast["cast_track_id"])
                        if cast["cast_track_id"] is not None
                        else None
                    )

                    impacts = tuple(
                        row
                        for row in events
                        if int(row["ability_game_id"]) == int(impact_ability_id)
                        and cast_time <= float(row["timestamp"]) <= window_end
                    )
                    if not impacts:
                        continue
                    preferred_impacts = self._prefer_cast_track(impacts, cast_track)
                    impact = min(
                        preferred_impacts,
                        key=lambda row: (float(row["timestamp"]), int(row["event_index"])),
                    )
                    impact_time = float(impact["timestamp"])
                    impact_observations += 1
                    cast_to_impact.append((impact_time - cast_time) / 1000.0)
                    if self._cast_track_matches(impact, cast_track):
                        linked_impacts += 1

                    periodic_rows = tuple(
                        row
                        for row in events
                        if int(row["ability_game_id"]) == int(periodic_ability_id)
                        and impact_time <= float(row["timestamp"]) <= window_end
                    )
                    if not periodic_rows:
                        continue
                    preferred_periodic = self._prefer_cast_track(periodic_rows, cast_track)
                    occurrence_times = self._cluster_occurrence_times(preferred_periodic)
                    if not occurrence_times:
                        continue
                    periodic_observations += 1
                    impact_to_periodic.append(
                        (occurrence_times[0] - impact_time) / 1000.0
                    )
                    periodic_intervals.extend(
                        (later - earlier) / 1000.0
                        for earlier, later in zip(
                            occurrence_times,
                            occurrence_times[1:],
                        )
                    )
                    linked_periodics += sum(
                        1
                        for row in periodic_rows
                        if self._cast_track_matches(row, cast_track)
                    )

        if impact_observations == 0:
            unresolved.append(
                f"{identity}: no impact ability {int(impact_ability_id)} observations found after casts"
            )
        if periodic_observations == 0:
            unresolved.append(
                f"{identity}: no periodic ability {int(periodic_ability_id)} observations found after impacts"
            )

        return self._report(
            identity,
            impact_ability_id=impact_ability_id,
            periodic_ability_id=periodic_ability_id,
            cast_count=cast_count,
            impact_observation_count=impact_observations,
            periodic_observation_count=periodic_observations,
            cast_track_linked_impact_count=linked_impacts,
            cast_track_linked_periodic_count=linked_periodics,
            cast_to_impact_seconds=tuple(cast_to_impact),
            impact_to_first_periodic_seconds=tuple(impact_to_periodic),
            periodic_intervals_seconds=tuple(periodic_intervals),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(
        self,
        skill_id: int,
        morph: int,
        base_ability_id: int,
    ) -> tuple[int, ...]:
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
                        "SELECT ability_id FROM skill_rank "
                        "WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
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
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'"
        ).fetchone()
        if row is None:
            return "log_event table is unavailable"
        required = {
            "report_code",
            "fight_id",
            "event_index",
            "timestamp",
            "event_type",
            "source_id",
            "ability_game_id",
            "cast_track_id",
            "raw_json",
        }
        columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(log_event)").fetchall()
        }
        missing = sorted(required - columns)
        return (
            "log_event is missing required columns: " + ", ".join(missing)
            if missing
            else None
        )

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
        ability_ids: tuple[int, int],
    ) -> tuple[sqlite3.Row, ...]:
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event "
                "WHERE report_code=? AND fight_id=? AND source_id=? "
                "AND ability_game_id IN (?,?) "
                "ORDER BY timestamp,event_index",
                (
                    report_code,
                    int(fight_id),
                    int(source_id),
                    int(ability_ids[0]),
                    int(ability_ids[1]),
                ),
            ).fetchall()
        )

    @classmethod
    def _matches_cast_identity(
        cls,
        row: sqlite3.Row,
        *,
        identity: str,
        aliases: set[int],
    ) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _prefer_cast_track(
        rows: tuple[sqlite3.Row, ...],
        cast_track: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        if cast_track is None:
            return rows
        linked = tuple(
            row
            for row in rows
            if row["cast_track_id"] is not None
            and int(row["cast_track_id"]) == cast_track
        )
        return linked or rows

    @staticmethod
    def _cast_track_matches(row: sqlite3.Row, cast_track: int | None) -> bool:
        return (
            cast_track is not None
            and row["cast_track_id"] is not None
            and int(row["cast_track_id"]) == cast_track
        )

    @classmethod
    def _cluster_occurrence_times(
        cls,
        rows: tuple[sqlite3.Row, ...],
    ) -> tuple[float, ...]:
        values = sorted(float(row["timestamp"]) for row in rows)
        clustered: list[float] = []
        for value in values:
            if not clustered or value - clustered[-1] > cls._OCCURRENCE_CLUSTER_MS:
                clustered.append(value)
        return tuple(clustered)

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
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _report(
        skill_entity_id: str,
        *,
        impact_ability_id: int,
        periodic_ability_id: int,
        cast_count: int = 0,
        impact_observation_count: int = 0,
        periodic_observation_count: int = 0,
        cast_track_linked_impact_count: int = 0,
        cast_track_linked_periodic_count: int = 0,
        cast_to_impact_seconds: tuple[float, ...] = (),
        impact_to_first_periodic_seconds: tuple[float, ...] = (),
        periodic_intervals_seconds: tuple[float, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsAnchorCorrelationReport:
        return RotationDDPeriodicEsoLogsAnchorCorrelationReport(
            skill_entity_id=skill_entity_id,
            impact_ability_id=int(impact_ability_id),
            periodic_ability_id=int(periodic_ability_id),
            cast_count=int(cast_count),
            impact_observation_count=int(impact_observation_count),
            periodic_observation_count=int(periodic_observation_count),
            cast_track_linked_impact_count=int(cast_track_linked_impact_count),
            cast_track_linked_periodic_count=int(cast_track_linked_periodic_count),
            cast_to_impact_seconds=cast_to_impact_seconds,
            impact_to_first_periodic_seconds=impact_to_first_periodic_seconds,
            periodic_intervals_seconds=periodic_intervals_seconds,
            unresolved=unresolved,
        )


__all__ = [
    "RotationDDPeriodicEsoLogsAnchorCorrelationReport",
    "RotationDDPeriodicEsoLogsAnchorCorrelationService",
]
