from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)
from services.rotation_reviewed_skill_source_repository import (
    RotationReviewedSkillSourceRepository,
    RotationSkillRuntimeSourceKind,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsPetSourceCandidate:
    ability_game_id: int
    ability_names: tuple[str, ...]
    cast_windows_observed: int
    event_count: int
    source_actor_count: int
    tick_marked_event_count: int
    reviewed_interval_match_count: int
    first_offset_samples_seconds: tuple[float, ...]
    interval_samples_seconds: tuple[float, ...]

    @property
    def median_first_offset_seconds(self) -> float | None:
        if not self.first_offset_samples_seconds:
            return None
        return float(median(self.first_offset_samples_seconds))


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsPetSourceDiscoveryReport:
    skill_entity_id: str
    cast_count: int
    reviewed_duration_seconds: float | None
    reviewed_interval_seconds: float | None
    candidates: tuple[RotationDDPeriodicEsoLogsPetSourceCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsPetSourceDiscoveryService:
    """Discover friendly non-player damage streams during reviewed pet-skill windows.

    Ordinary periodic discovery intentionally stays player-source strict. Pet skills
    need a separate observational path because ESO Logs may attribute autonomous pet
    attacks to a distinct source actor. This service therefore looks at friendly
    damage from sources that are either absent from imported ``log_actor`` player
    metadata or explicitly typed as pet/companion/summon-like.

    The imported corpus does not currently preserve a reliable pet->owner relation.
    Candidate events are therefore never claimed as owned by the caster merely
    because they occur inside the summon window. This service ranks evidence only.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _PET_ACTOR_TYPES = frozenset({"pet", "companion", "summon", "summoned"})
    _INTERVAL_TOLERANCE_SECONDS = 0.15

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
        source_repository: RotationReviewedSkillSourceRepository | None = None,
    ) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)
        self.review_service = review_service or RotationDDPeriodicRuntimeSemanticsReviewService()
        self.source_repository = source_repository or RotationReviewedSkillSourceRepository()

    def inspect_skill(
        self,
        skill_entity_id: str,
        *,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
        max_candidates: int = 12,
    ) -> RotationDDPeriodicEsoLogsPetSourceDiscoveryReport:
        identity = ability_entity_id(skill_entity_id)
        if not identity:
            return self._report("", unresolved=("canonical skill identity is required",))

        source_review = self.source_repository.resolve(identity)
        if source_review is None or source_review.source_kind is not RotationSkillRuntimeSourceKind.PET:
            return self._report(
                identity,
                unresolved=(f"{identity}: reviewed runtime source is not pet-owned",),
            )

        duration, interval, review_unresolved = self._review_window(identity)
        if duration is None:
            return self._report(
                identity,
                reviewed_interval_seconds=interval,
                unresolved=review_unresolved,
            )

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        unresolved = list(review_unresolved)
        if resolution.rank is not None:
            aliases.update(self._numeric_aliases(resolution.rank.skill_id, resolution.rank.morph))
            if int(resolution.rank.base_ability_id) > 0:
                aliases.add(int(resolution.rank.base_ability_id))
        else:
            unresolved.extend(resolution.unresolved)

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(
                    identity,
                    reviewed_duration_seconds=duration,
                    reviewed_interval_seconds=interval,
                    unresolved=tuple(dict.fromkeys((*unresolved, schema_error))),
                )

            casts = self._matching_casts(
                db,
                identity=identity,
                aliases=aliases,
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
            )
            if not casts:
                unresolved.append(f"{identity}: no matching ESO Logs cast observations found")
                return self._report(
                    identity,
                    reviewed_duration_seconds=duration,
                    reviewed_interval_seconds=interval,
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            observations: dict[int, dict[str, object]] = {}
            grouped: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
            for cast in casts:
                if cast["source_id"] is None:
                    continue
                key = (
                    str(cast["report_code"]),
                    int(cast["fight_id"]),
                    int(cast["source_id"]),
                )
                grouped.setdefault(key, []).append(cast)

            cast_count = 0
            for key, group_casts in grouped.items():
                ordered = sorted(
                    group_casts,
                    key=lambda row: (float(row["timestamp"]), int(row["event_index"])),
                )
                for index, cast in enumerate(ordered):
                    cast_count += 1
                    cast_time = float(cast["timestamp"])
                    natural_end = cast_time + duration * 1000.0
                    next_cast = (
                        float(ordered[index + 1]["timestamp"])
                        if index + 1 < len(ordered)
                        else None
                    )
                    window_end = min(natural_end, next_cast) if next_cast is not None else natural_end
                    rows = self._pet_damage_rows(
                        db,
                        report_code=key[0],
                        fight_id=key[1],
                        caster_source_id=key[2],
                        start_time=cast_time,
                        end_time=window_end,
                    )
                    self._accumulate_window(
                        observations,
                        rows=rows,
                        cast=cast,
                        reviewed_interval_seconds=interval,
                    )

        candidates = self._build_candidates(observations)
        if max_candidates > 0:
            candidates = candidates[: int(max_candidates)]
        if not candidates:
            unresolved.append(
                f"{identity}: no friendly non-player damage candidates were observed inside reviewed pet windows"
            )
        unresolved.append(
            f"{identity}: pet-source candidates are not owner-linked to the caster in this imported corpus"
        )
        return self._report(
            identity,
            cast_count=cast_count,
            reviewed_duration_seconds=duration,
            reviewed_interval_seconds=interval,
            candidates=tuple(candidates),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _review_window(self, identity: str) -> tuple[float | None, float | None, tuple[str, ...]]:
        rows = tuple(
            row
            for (entity, _coefficient), row in self.review_service.by_component().items()
            if entity == identity
        )
        durations = {float(row.duration_seconds) for row in rows if row.duration_seconds is not None}
        intervals = {
            float(row.reviewed_interval_seconds)
            for row in rows
            if row.reviewed_interval_seconds is not None
        }
        unresolved: list[str] = []
        duration = next(iter(durations)) if len(durations) == 1 else None
        interval = next(iter(intervals)) if len(intervals) == 1 else None
        if duration is None:
            unresolved.append(f"{identity}: one unambiguous reviewed duration is required")
        if len(durations) > 1:
            unresolved.append(f"{identity}: conflicting reviewed durations")
        if len(intervals) > 1:
            unresolved.append(f"{identity}: conflicting reviewed intervals")
        return duration, interval, tuple(unresolved)

    def _matching_casts(
        self,
        db: sqlite3.Connection,
        *,
        identity: str,
        aliases: set[int],
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        where = ["lower(event_type) IN ('cast','completecast','begincast')"]
        params: list[object] = []
        if report_code is not None:
            where.append("report_code = ?")
            params.append(str(report_code))
        if fight_id is not None:
            where.append("fight_id = ?")
            params.append(int(fight_id))
        if source_id is not None:
            where.append("source_id = ?")
            params.append(int(source_id))
        rows = db.execute(
            "SELECT * FROM log_event WHERE " + " AND ".join(where) + " ORDER BY report_code, fight_id, timestamp, event_index",
            tuple(params),
        ).fetchall()
        matched = tuple(row for row in rows if self._matches_identity(row, identity=identity, aliases=aliases))
        if not matched:
            return ()
        for event_type in self._CAST_TYPES:
            typed = tuple(row for row in matched if str(row["event_type"] or "").casefold() == event_type)
            if typed:
                return typed
        return ()

    def _pet_damage_rows(
        self,
        db: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        caster_source_id: int,
        start_time: float,
        end_time: float,
    ) -> tuple[sqlite3.Row, ...]:
        return tuple(
            db.execute(
                """
                SELECT e.*, a.actor_type AS source_actor_type
                FROM log_event e
                LEFT JOIN log_actor a
                  ON a.report_code = e.report_code
                 AND a.fight_id = e.fight_id
                 AND a.actor_id = e.source_id
                WHERE e.report_code = ?
                  AND e.fight_id = ?
                  AND lower(e.event_type) = 'damage'
                  AND e.timestamp >= ?
                  AND e.timestamp <= ?
                  AND e.source_id IS NOT NULL
                  AND e.source_id != ?
                  AND COALESCE(e.source_is_friendly, 0) = 1
                  AND (
                        a.actor_id IS NULL
                        OR lower(COALESCE(a.actor_type, '')) IN ('pet','companion','summon','summoned')
                  )
                ORDER BY e.timestamp, e.event_index
                """,
                (report_code, int(fight_id), float(start_time), float(end_time), int(caster_source_id)),
            ).fetchall()
        )

    def _accumulate_window(
        self,
        observations: dict[int, dict[str, object]],
        *,
        rows: tuple[sqlite3.Row, ...],
        cast: sqlite3.Row,
        reviewed_interval_seconds: float | None,
    ) -> None:
        by_ability: dict[int, list[sqlite3.Row]] = {}
        for row in rows:
            if row["ability_game_id"] is None:
                continue
            by_ability.setdefault(int(row["ability_game_id"]), []).append(row)

        cast_time = float(cast["timestamp"])
        window_id = (
            str(cast["report_code"]),
            int(cast["fight_id"]),
            int(cast["source_id"]),
            cast_time,
        )
        for ability_id, ability_rows in by_ability.items():
            by_source: dict[int, list[sqlite3.Row]] = {}
            for row in ability_rows:
                by_source.setdefault(int(row["source_id"]), []).append(row)
            stream_intervals: list[float] = []
            first_offsets: list[float] = []
            for source_rows in by_source.values():
                times = sorted(dict.fromkeys(float(row["timestamp"]) for row in source_rows))
                if not times:
                    continue
                first_offsets.append((times[0] - cast_time) / 1000.0)
                stream_intervals.extend(
                    (later - earlier) / 1000.0
                    for earlier, later in zip(times, times[1:])
                )
            if not first_offsets:
                continue

            bucket = observations.setdefault(
                ability_id,
                {
                    "names": set(),
                    "windows": set(),
                    "events": set(),
                    "sources": set(),
                    "tick_count": 0,
                    "first_offsets": [],
                    "intervals": [],
                    "interval_matches": 0,
                },
            )
            bucket["windows"].add(window_id)
            bucket["first_offsets"].extend(first_offsets)
            bucket["intervals"].extend(stream_intervals)
            if reviewed_interval_seconds is not None:
                bucket["interval_matches"] += sum(
                    1
                    for value in stream_intervals
                    if math.isclose(
                        value,
                        reviewed_interval_seconds,
                        rel_tol=0.0,
                        abs_tol=self._INTERVAL_TOLERANCE_SECONDS,
                    )
                )
            for row in ability_rows:
                name = self._ability_name(row["raw_json"])
                if name:
                    bucket["names"].add(name)
                bucket["events"].add(
                    (str(row["report_code"]), int(row["fight_id"]), int(row["event_index"]))
                )
                bucket["sources"].add(
                    (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
                )
                if bool(row["tick"]):
                    bucket["tick_count"] += 1

    @staticmethod
    def _build_candidates(
        observations: dict[int, dict[str, object]],
    ) -> list[RotationDDPeriodicEsoLogsPetSourceCandidate]:
        candidates = [
            RotationDDPeriodicEsoLogsPetSourceCandidate(
                ability_game_id=int(ability_id),
                ability_names=tuple(sorted(data["names"], key=str.casefold)),
                cast_windows_observed=len(data["windows"]),
                event_count=len(data["events"]),
                source_actor_count=len(data["sources"]),
                tick_marked_event_count=int(data["tick_count"]),
                reviewed_interval_match_count=int(data["interval_matches"]),
                first_offset_samples_seconds=tuple(float(value) for value in data["first_offsets"]),
                interval_samples_seconds=tuple(float(value) for value in data["intervals"]),
            )
            for ability_id, data in observations.items()
        ]
        candidates.sort(
            key=lambda item: (
                -item.reviewed_interval_match_count,
                -item.cast_windows_observed,
                -item.event_count,
                item.ability_game_id,
            )
        )
        return candidates

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            return tuple(
                sorted(
                    int(row["ability_id"])
                    for row in db.execute(
                        "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
                        (int(skill_id), int(morph)),
                    ).fetchall()
                )
            )

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        tables = {
            str(row[0])
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing_tables = sorted({"log_event", "log_actor"} - tables)
        if missing_tables:
            return "missing required tables: " + ", ".join(missing_tables)
        required = {
            "report_code",
            "fight_id",
            "event_index",
            "timestamp",
            "event_type",
            "source_id",
            "source_is_friendly",
            "ability_game_id",
            "tick",
            "raw_json",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None

    @classmethod
    def _matches_identity(cls, row: sqlite3.Row, *, identity: str, aliases: set[int]) -> bool:
        name = cls._ability_name(row["raw_json"])
        if name:
            return ability_entity_id(name) == identity
        return row["ability_game_id"] is not None and int(row["ability_game_id"]) in aliases

    @staticmethod
    def _ability_name(raw_json) -> str | None:
        try:
            payload = json.loads(str(raw_json or ""))
        except (TypeError, json.JSONDecodeError):
            return None
        ability = payload.get("ability") if isinstance(payload, dict) else None
        if isinstance(ability, dict):
            text = str(ability.get("name") or "").strip()
            return text or None
        return None

    @staticmethod
    def _report(
        identity: str,
        *,
        cast_count: int = 0,
        reviewed_duration_seconds: float | None = None,
        reviewed_interval_seconds: float | None = None,
        candidates: tuple[RotationDDPeriodicEsoLogsPetSourceCandidate, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsPetSourceDiscoveryReport:
        return RotationDDPeriodicEsoLogsPetSourceDiscoveryReport(
            skill_entity_id=identity,
            cast_count=int(cast_count),
            reviewed_duration_seconds=reviewed_duration_seconds,
            reviewed_interval_seconds=reviewed_interval_seconds,
            candidates=tuple(candidates),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "RotationDDPeriodicEsoLogsPetSourceCandidate",
    "RotationDDPeriodicEsoLogsPetSourceDiscoveryReport",
    "RotationDDPeriodicEsoLogsPetSourceDiscoveryService",
]
