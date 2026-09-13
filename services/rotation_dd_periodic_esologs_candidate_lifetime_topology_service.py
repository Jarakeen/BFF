from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateLifetimeGroup:
    candidate_ability_id: int
    time_band: str
    source_relation: str
    track_relation: str
    observation_count: int
    cast_window_count: int
    distinct_source_count: int
    distinct_target_count: int
    distinct_track_count: int
    median_offset_seconds: float | None
    latest_offset_seconds: float | None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateLifetimeTopologyReport:
    skill_entity_id: str
    candidate_ability_ids: tuple[int, ...]
    active_window_seconds: float
    cast_count: int
    observation_count: int
    unique_event_count: int
    overlapping_window_reuse_count: int
    groups: tuple[RotationDDPeriodicEsoLogsCandidateLifetimeGroup, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService:
    """Observe candidate source/track/target topology across one cast lifetime.

    The probe is intentionally observational. Candidate numeric IDs are evidence
    handles only. Events are compared with each matching canonical skill cast by
    report/fight and timestamp, then classified by whether they share the cast's
    source actor and cast-track id. A candidate event may appear in more than one
    overlapping cast window; the report exposes that reuse rather than silently
    assigning ownership to one cast.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _TIME_BANDS = (
        (0.0, 2.0, "0-2s"),
        (2.0, 5.0, "2-5s"),
        (5.0, 10.0, "5-10s"),
        (10.0, float("inf"), "10s+"),
    )

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
        candidate_ability_ids: tuple[int, ...],
        active_window_seconds: float,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsCandidateLifetimeTopologyReport:
        identity = ability_entity_id(skill_entity_id)
        candidates = tuple(dict.fromkeys(int(value) for value in candidate_ability_ids))
        window = float(active_window_seconds)
        if not identity:
            return self._report("", candidates, window, unresolved=("canonical skill identity is required",))
        if not candidates or any(value <= 0 for value in candidates):
            return self._report(identity, candidates, window, unresolved=("positive candidate ability ids are required",))
        if window <= 0:
            return self._report(identity, candidates, window, unresolved=("active_window_seconds must be positive",))
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        unresolved: list[str] = []
        if resolution.rank is not None:
            aliases.add(int(resolution.rank.base_ability_id))
            aliases.update(self._numeric_aliases(resolution.rank.skill_id, resolution.rank.morph))
        elif resolution.unresolved:
            unresolved.extend(str(value) for value in resolution.unresolved if str(value).strip())

        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(identity, candidates, window, unresolved=(schema_error,))
            rows = self._rows(
                db,
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
                include_other_sources=True,
            )

        casts = [
            row
            for row in rows
            if self._event_type(row) in self._CAST_TYPES
            and self._matches_cast(row, identity=identity, aliases=aliases)
            and (source_id is None or row["source_id"] == int(source_id))
        ]
        if not casts:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, candidates, window, unresolved=tuple(dict.fromkeys(unresolved)))
        anchor_type = next(
            kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts)
        )
        casts = [row for row in casts if self._event_type(row) == anchor_type]

        candidate_set = set(candidates)
        candidate_rows_by_scope: dict[tuple[str, int], list[sqlite3.Row]] = {}
        for row in rows:
            ability = row["ability_game_id"]
            if ability is None or int(ability) not in candidate_set:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]))
            candidate_rows_by_scope.setdefault(key, []).append(row)

        raw_groups: dict[
            tuple[int, str, str, str],
            dict[str, object],
        ] = {}
        unique_events: set[tuple[str, int, int]] = set()
        observation_count = 0

        for cast in casts:
            cast_time = float(cast["timestamp"])
            cast_source = self._int_or_none(cast["source_id"])
            cast_track = self._int_or_none(cast["cast_track_id"])
            scope = (str(cast["report_code"]), int(cast["fight_id"]))
            window_end = cast_time + window * 1000.0
            cast_key = (scope[0], scope[1], int(cast["event_index"]))
            for row in candidate_rows_by_scope.get(scope, ()):
                timestamp = float(row["timestamp"])
                if timestamp < cast_time or timestamp > window_end:
                    continue
                offset = (timestamp - cast_time) / 1000.0
                candidate_id = int(row["ability_game_id"])
                event_source = self._int_or_none(row["source_id"])
                event_track = self._int_or_none(row["cast_track_id"])
                source_relation = "same_source" if cast_source is not None and event_source == cast_source else "other_source"
                if event_track is None:
                    track_relation = "missing_track"
                elif cast_track is not None and event_track == cast_track:
                    track_relation = "same_track"
                else:
                    track_relation = "other_track"
                band = self._time_band(offset, window)
                key = (candidate_id, band, source_relation, track_relation)
                bucket = raw_groups.setdefault(
                    key,
                    {
                        "observations": 0,
                        "casts": set(),
                        "sources": set(),
                        "targets": set(),
                        "tracks": set(),
                        "offsets": [],
                    },
                )
                bucket["observations"] = int(bucket["observations"]) + 1
                bucket["casts"].add(cast_key)  # type: ignore[union-attr]
                if event_source is not None:
                    bucket["sources"].add(event_source)  # type: ignore[union-attr]
                target = self._int_or_none(row["target_id"])
                if target is not None:
                    bucket["targets"].add(target)  # type: ignore[union-attr]
                if event_track is not None:
                    bucket["tracks"].add(event_track)  # type: ignore[union-attr]
                bucket["offsets"].append(offset)  # type: ignore[union-attr]
                observation_count += 1
                unique_events.add((scope[0], scope[1], int(row["event_index"])))

        groups: list[RotationDDPeriodicEsoLogsCandidateLifetimeGroup] = []
        for (candidate_id, band, source_relation, track_relation), bucket in sorted(raw_groups.items()):
            offsets = tuple(float(value) for value in bucket["offsets"])  # type: ignore[arg-type]
            groups.append(
                RotationDDPeriodicEsoLogsCandidateLifetimeGroup(
                    candidate_ability_id=candidate_id,
                    time_band=band,
                    source_relation=source_relation,
                    track_relation=track_relation,
                    observation_count=int(bucket["observations"]),
                    cast_window_count=len(bucket["casts"]),  # type: ignore[arg-type]
                    distinct_source_count=len(bucket["sources"]),  # type: ignore[arg-type]
                    distinct_target_count=len(bucket["targets"]),  # type: ignore[arg-type]
                    distinct_track_count=len(bucket["tracks"]),  # type: ignore[arg-type]
                    median_offset_seconds=float(median(offsets)) if offsets else None,
                    latest_offset_seconds=max(offsets) if offsets else None,
                )
            )

        if not groups:
            unresolved.append(f"{identity}: no candidate events observed inside reviewed cast windows")
        unique_event_count = len(unique_events)
        return self._report(
            identity,
            candidates,
            window,
            cast_count=len(casts),
            observation_count=observation_count,
            unique_event_count=unique_event_count,
            overlapping_window_reuse_count=max(0, observation_count - unique_event_count),
            groups=tuple(groups),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _time_band(cls, offset_seconds: float, active_window_seconds: float) -> str:
        offset = max(0.0, float(offset_seconds))
        for start, end, label in cls._TIME_BANDS:
            effective_end = min(end, float(active_window_seconds))
            if start <= offset < effective_end or (
                offset == float(active_window_seconds) and effective_end == float(active_window_seconds)
            ):
                return label
        return f">{active_window_seconds:g}s"

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            rows = db.execute(
                "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? "
                "AND ability_id IS NOT NULL",
                (int(skill_id), int(morph)),
            ).fetchall()
        return tuple(int(row[0]) for row in rows)

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'").fetchone()
        if table is None:
            return "log_event table is unavailable"
        required = {
            "report_code", "fight_id", "event_index", "timestamp", "event_type",
            "source_id", "target_id", "ability_game_id", "cast_track_id", "raw_json",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None

    @staticmethod
    def _rows(
        db: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
        include_other_sources: bool,
    ) -> tuple[sqlite3.Row, ...]:
        clauses = ["1=1"]
        params: list[object] = []
        if report_code is not None:
            clauses.append("report_code=?")
            params.append(str(report_code))
        if fight_id is not None:
            clauses.append("fight_id=?")
            params.append(int(fight_id))
        if source_id is not None and not include_other_sources:
            clauses.append("source_id=?")
            params.append(int(source_id))
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,target_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,timestamp,event_index",
                tuple(params),
            ).fetchall()
        )

    @classmethod
    def _matches_cast(cls, row: sqlite3.Row, *, identity: str, aliases: set[int]) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _ability_name_from_raw(raw_json: object) -> str | None:
        if raw_json is None:
            return None
        try:
            payload = json.loads(str(raw_json))
        except (TypeError, json.JSONDecodeError):
            return None
        ability = payload.get("ability") if isinstance(payload, dict) else None
        if not isinstance(ability, dict):
            return None
        value = ability.get("name")
        return str(value).strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().casefold()

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _report(
        skill: str,
        candidates: tuple[int, ...],
        window: float,
        **kwargs,
    ) -> RotationDDPeriodicEsoLogsCandidateLifetimeTopologyReport:
        return RotationDDPeriodicEsoLogsCandidateLifetimeTopologyReport(
            skill_entity_id=skill,
            candidate_ability_ids=candidates,
            active_window_seconds=window,
            cast_count=kwargs.get("cast_count", 0),
            observation_count=kwargs.get("observation_count", 0),
            unique_event_count=kwargs.get("unique_event_count", 0),
            overlapping_window_reuse_count=kwargs.get("overlapping_window_reuse_count", 0),
            groups=kwargs.get("groups", ()),
            unresolved=kwargs.get("unresolved", ()),
        )


__all__ = [
    "RotationDDPeriodicEsoLogsCandidateLifetimeGroup",
    "RotationDDPeriodicEsoLogsCandidateLifetimeTopologyReport",
    "RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService",
]
