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


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsSecondaryEffectCandidate:
    """One observational damage identity repeatedly seen after a reviewed skill cast."""

    ability_entity_id: str
    ability_names: tuple[str, ...]
    ability_game_ids: tuple[int, ...]
    cast_windows_observed: int
    event_count: int
    occurrence_count: int
    tick_marked_event_count: int
    cast_track_linked_event_count: int
    first_offset_samples_seconds: tuple[float, ...]
    interval_samples_seconds: tuple[float, ...]
    reviewed_interval_match_count: int

    @property
    def median_first_offset_seconds(self) -> float | None:
        if not self.first_offset_samples_seconds:
            return None
        return float(median(self.first_offset_samples_seconds))


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport:
    skill_entity_id: str
    cast_count: int
    reviewed_duration_seconds: float | None
    reviewed_interval_seconds: float | None
    candidates: tuple[RotationDDPeriodicEsoLogsSecondaryEffectCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService:
    """Discover possible secondary DoT event identities without promoting them.

    ESO Logs frequently records a skill cast under one ability identity and its
    periodic damage under a different effect identity.  This service anchors on the
    canonical cast skill, then inspects other damage identities from the same source
    inside the reviewed active window.  Candidate ranking is observational only.

    Canonical lower-snake skill identity remains authoritative. Numeric ability ids
    are source crosswalks only. A translated raw ability name wins over a numeric id.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _INTERVAL_TOLERANCE_SECONDS = 0.15

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
    ) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)
        self.review_service = review_service or RotationDDPeriodicRuntimeSemanticsReviewService()

    def inspect_skill(
        self,
        skill_entity_id: str,
        *,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
        max_candidates: int = 12,
    ) -> RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport:
        identity = ability_entity_id(skill_entity_id)
        if not identity:
            return self._report("", unresolved=("canonical skill identity is required",))
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)

        review_rows = tuple(
            row
            for (entity, _coefficient), row in self.review_service.by_component().items()
            if entity == identity
        )
        durations = {
            float(row.duration_seconds)
            for row in review_rows
            if row.duration_seconds is not None
        }
        intervals = {
            float(row.reviewed_interval_seconds)
            for row in review_rows
            if row.reviewed_interval_seconds is not None
        }
        unresolved: list[str] = []
        duration = next(iter(durations)) if len(durations) == 1 else None
        reviewed_interval = next(iter(intervals)) if len(intervals) == 1 else None
        if duration is None:
            unresolved.append(
                f"{identity}: one unambiguous reviewed duration is required for secondary-effect discovery"
            )
        if len(durations) > 1:
            unresolved.append(f"{identity}: conflicting reviewed durations")
        if len(intervals) > 1:
            unresolved.append(f"{identity}: conflicting reviewed intervals")
        if duration is None:
            return self._report(
                identity,
                reviewed_duration_seconds=None,
                reviewed_interval_seconds=reviewed_interval,
                unresolved=tuple(unresolved),
            )

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        if resolution.rank is not None:
            aliases.update(self._numeric_aliases(resolution.rank.skill_id, resolution.rank.morph))
            if int(resolution.rank.base_ability_id) > 0:
                aliases.add(int(resolution.rank.base_ability_id))
        elif resolution.unresolved:
            unresolved.extend(str(item).strip() for item in resolution.unresolved if str(item).strip())

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(
                    identity,
                    reviewed_duration_seconds=duration,
                    reviewed_interval_seconds=reviewed_interval,
                    unresolved=tuple(dict.fromkeys((*unresolved, schema_error))),
                )
            rows = self._candidate_rows(
                db,
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
            )

        cast_rows = tuple(
            row
            for row in rows
            if self._event_type(row) in self._CAST_TYPES
            and self._matches_cast_identity(row, identity=identity, aliases=aliases)
        )
        if not cast_rows:
            unresolved.append(f"{identity}: no matching ESO Logs cast observations found")
            return self._report(
                identity,
                reviewed_duration_seconds=duration,
                reviewed_interval_seconds=reviewed_interval,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        anchor_type = next(
            kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in cast_rows)
        )
        anchors = tuple(row for row in cast_rows if self._event_type(row) == anchor_type)
        grouped_anchors: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for cast in anchors:
            if cast["source_id"] is None:
                continue
            key = (str(cast["report_code"]), int(cast["fight_id"]), int(cast["source_id"]))
            grouped_anchors.setdefault(key, []).append(cast)

        damage_by_group: dict[tuple[str, int, int], tuple[sqlite3.Row, ...]] = {}
        for row in rows:
            if self._event_type(row) != "damage" or row["source_id"] is None:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
            if key in grouped_anchors:
                damage_by_group.setdefault(key, ())
                damage_by_group[key] = (*damage_by_group[key], row)

        observations: dict[str, dict[str, object]] = {}
        cast_count = 0
        for key, casts in grouped_anchors.items():
            casts = sorted(casts, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            damages = damage_by_group.get(key, ())
            for index, cast in enumerate(casts):
                cast_count += 1
                cast_time = float(cast["timestamp"])
                natural_end = cast_time + duration * 1000.0
                next_cast = float(casts[index + 1]["timestamp"]) if index + 1 < len(casts) else None
                window_end = min(natural_end, next_cast) if next_cast is not None else natural_end
                cast_track_id = int(cast["cast_track_id"]) if cast["cast_track_id"] is not None else None

                window_rows = tuple(
                    row
                    for row in damages
                    if cast_time <= float(row["timestamp"]) <= window_end
                    and not self._matches_cast_identity(row, identity=identity, aliases=aliases)
                )
                per_stream: dict[str, list[sqlite3.Row]] = {}
                for row in window_rows:
                    stream_key = self._stream_key(row)
                    if not stream_key:
                        continue
                    per_stream.setdefault(stream_key, []).append(row)

                for stream_key, stream_rows in per_stream.items():
                    times = tuple(sorted(dict.fromkeys(float(row["timestamp"]) for row in stream_rows)))
                    linked_count = sum(
                        1
                        for row in stream_rows
                        if cast_track_id is not None
                        and row["cast_track_id"] is not None
                        and int(row["cast_track_id"]) == cast_track_id
                    )
                    # One unlinked direct hit is not useful as a periodic candidate.
                    if len(times) < 2 and linked_count == 0:
                        continue
                    bucket = observations.setdefault(
                        stream_key,
                        {
                            "names": set(),
                            "ids": set(),
                            "windows": set(),
                            "events": set(),
                            "occurrences": set(),
                            "tick_count": 0,
                            "linked_count": 0,
                            "first_offsets": [],
                            "intervals": [],
                            "interval_matches": 0,
                        },
                    )
                    window_id = (key, float(cast["timestamp"]))
                    bucket["windows"].add(window_id)
                    bucket["first_offsets"].append((times[0] - cast_time) / 1000.0)
                    stream_intervals = tuple(
                        (later - earlier) / 1000.0 for earlier, later in zip(times, times[1:])
                    )
                    bucket["intervals"].extend(stream_intervals)
                    if reviewed_interval is not None:
                        bucket["interval_matches"] += sum(
                            1
                            for value in stream_intervals
                            if math.isclose(
                                value,
                                reviewed_interval,
                                rel_tol=0.0,
                                abs_tol=self._INTERVAL_TOLERANCE_SECONDS,
                            )
                        )
                    for row in stream_rows:
                        name = self._ability_name_from_raw(row["raw_json"])
                        if name:
                            bucket["names"].add(name)
                        if row["ability_game_id"] is not None:
                            bucket["ids"].add(int(row["ability_game_id"]))
                        event_id = (
                            str(row["report_code"]),
                            int(row["fight_id"]),
                            int(row["event_index"]),
                        )
                        bucket["events"].add(event_id)
                        bucket["occurrences"].add(
                            (str(row["report_code"]), int(row["fight_id"]), float(row["timestamp"]))
                        )
                        if bool(row["tick"]):
                            bucket["tick_count"] += 1
                    bucket["linked_count"] += linked_count

        candidates = [
            RotationDDPeriodicEsoLogsSecondaryEffectCandidate(
                ability_entity_id=stream_key,
                ability_names=tuple(sorted(data["names"], key=str.casefold)),
                ability_game_ids=tuple(sorted(data["ids"])),
                cast_windows_observed=len(data["windows"]),
                event_count=len(data["events"]),
                occurrence_count=len(data["occurrences"]),
                tick_marked_event_count=int(data["tick_count"]),
                cast_track_linked_event_count=int(data["linked_count"]),
                first_offset_samples_seconds=tuple(float(value) for value in data["first_offsets"]),
                interval_samples_seconds=tuple(float(value) for value in data["intervals"]),
                reviewed_interval_match_count=int(data["interval_matches"]),
            )
            for stream_key, data in observations.items()
        ]
        candidates.sort(
            key=lambda item: (
                -item.cast_track_linked_event_count,
                -item.reviewed_interval_match_count,
                -item.cast_windows_observed,
                -item.occurrence_count,
                item.ability_entity_id,
            )
        )
        if max_candidates > 0:
            candidates = candidates[: int(max_candidates)]

        if not candidates:
            unresolved.append(
                f"{identity}: no repeated secondary damage identities were observed inside reviewed cast windows"
            )

        return self._report(
            identity,
            cast_count=cast_count,
            reviewed_duration_seconds=duration,
            reviewed_interval_seconds=reviewed_interval,
            candidates=tuple(candidates),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_rank'"
            ).fetchone()
            if table is None:
                return ()
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
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'"
        ).fetchone()
        if row is None:
            return "log_event table is unavailable"
        required = {
            "report_code", "fight_id", "event_index", "timestamp", "event_type",
            "source_id", "ability_game_id", "tick", "cast_track_id", "raw_json",
        }
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()}
        missing = sorted(required - columns)
        return "log_event is missing required columns: " + ", ".join(missing) if missing else None

    @staticmethod
    def _candidate_rows(
        db: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        clauses = ["lower(event_type) IN ('cast','begincast','completecast','damage')"]
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
                "ability_game_id,tick,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()
        )

    @classmethod
    def _matches_cast_identity(cls, row: sqlite3.Row, *, identity: str, aliases: set[int]) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @classmethod
    def _stream_key(cls, row: sqlite3.Row) -> str:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name)
        value = row["ability_game_id"]
        return f"ability_id_{int(value)}" if value is not None else ""

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
        cast_count: int = 0,
        reviewed_duration_seconds: float | None = None,
        reviewed_interval_seconds: float | None = None,
        candidates: tuple[RotationDDPeriodicEsoLogsSecondaryEffectCandidate, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport:
        return RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport(
            skill_entity_id=skill_entity_id,
            cast_count=cast_count,
            reviewed_duration_seconds=reviewed_duration_seconds,
            reviewed_interval_seconds=reviewed_interval_seconds,
            candidates=candidates,
            unresolved=unresolved,
        )


__all__ = [
    "RotationDDPeriodicEsoLogsSecondaryEffectCandidate",
    "RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport",
    "RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService",
]
