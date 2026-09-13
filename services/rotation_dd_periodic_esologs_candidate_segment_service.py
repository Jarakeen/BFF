from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from services.rotation_dd_periodic_esologs_candidate_continuity_service import (
    RotationDDPeriodicEsoLogsCandidateContinuityService,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateSegmentSummary:
    candidate_ability_id: int
    linked_cast_count: int
    multi_segment_cast_count: int
    median_segments_per_cast: float | None
    maximum_segments_per_cast: int | None
    median_segment_duration_seconds: float | None
    median_occurrences_per_segment: float | None
    median_inter_segment_gap_seconds: float | None
    maximum_inter_segment_gap_seconds: float | None
    resumed_at_or_after_5s: int
    resumed_at_or_after_10s: int
    resumed_at_or_after_15s: int


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateSegmentReport:
    skill_entity_id: str
    candidate_ability_ids: tuple[int, ...]
    active_window_seconds: float
    cluster_tolerance_seconds: float
    segment_gap_seconds: float
    cast_count: int
    summaries: tuple[RotationDDPeriodicEsoLogsCandidateSegmentSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsCandidateSegmentService:
    """Observe burst/segment structure within censored candidate cast-track streams.

    Candidate IDs remain observational evidence handles only. Same-source, same-track
    events are censored at the next same-source cast, reviewed active-window end, or
    imported fight end. Near-simultaneous fan-out is collapsed before segmentation.
    A new segment begins only when the gap between clustered occurrences is greater
    than ``segment_gap_seconds``. Segment structure never promotes executable cadence,
    duration, or conditional-runtime semantics automatically.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")

    def __init__(self, *, canonical_database_path: str | Path, logs_database_path: str | Path) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)

    def inspect(
        self,
        skill_entity_id: str,
        *,
        candidate_ability_ids: tuple[int, ...],
        active_window_seconds: float,
        cluster_tolerance_seconds: float = 0.05,
        segment_gap_seconds: float = 2.0,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsCandidateSegmentReport:
        identity = ability_entity_id(skill_entity_id)
        candidates = tuple(dict.fromkeys(int(value) for value in candidate_ability_ids))
        window = float(active_window_seconds)
        tolerance = float(cluster_tolerance_seconds)
        segment_gap = float(segment_gap_seconds)
        if not identity:
            return self._report("", candidates, window, tolerance, segment_gap, unresolved=("canonical skill identity is required",))
        if not candidates or any(value <= 0 for value in candidates):
            return self._report(identity, candidates, window, tolerance, segment_gap, unresolved=("positive candidate ability ids are required",))
        if window <= 0 or tolerance < 0 or segment_gap <= 0:
            return self._report(identity, candidates, window, tolerance, segment_gap, unresolved=("window and segment gap must be positive; cluster tolerance cannot be negative",))
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
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {"report_code", "fight_id", "event_index", "timestamp", "event_type", "source_id", "ability_game_id", "cast_track_id", "raw_json"}
            missing = sorted(required - columns)
            if missing:
                return self._report(identity, candidates, window, tolerance, segment_gap, unresolved=("log_event missing required columns: " + ", ".join(missing),))
            clauses = ["1=1"]
            params: list[object] = []
            if report_code is not None:
                clauses.append("report_code=?")
                params.append(str(report_code))
            if fight_id is not None:
                clauses.append("fight_id=?")
                params.append(int(fight_id))
            rows = tuple(db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall())

        casts = [row for row in rows if self._event_type(row) in self._CAST_TYPES and self._matches_cast(row, identity, aliases) and (source_id is None or self._int_or_none(row["source_id"]) == int(source_id))]
        if not casts:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, candidates, window, tolerance, segment_gap, unresolved=tuple(dict.fromkeys(unresolved)))
        anchor_type = next(kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts))
        casts = [row for row in casts if self._event_type(row) == anchor_type]
        next_cast_times = self._next_same_source_cast_times(casts)
        fight_end_times = self._fight_end_times(rows)

        candidate_set = set(candidates)
        by_scope_source_track: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            ability = row["ability_game_id"]
            source = self._int_or_none(row["source_id"])
            track = self._int_or_none(row["cast_track_id"])
            if ability is None or int(ability) not in candidate_set or source is None or track is None:
                continue
            by_scope_source_track.setdefault((str(row["report_code"]), int(row["fight_id"]), source, track), []).append(row)

        streams_by_candidate: dict[int, list[tuple[float, ...]]] = {candidate: [] for candidate in candidates}
        tolerance_ms = tolerance * 1000.0
        for cast in casts:
            cast_source = self._int_or_none(cast["source_id"])
            cast_track = self._int_or_none(cast["cast_track_id"])
            if cast_source is None or cast_track is None:
                continue
            cast_time = float(cast["timestamp"])
            report = str(cast["report_code"])
            fight = int(cast["fight_id"])
            cast_key = (report, fight, int(cast["event_index"]))
            next_cast_time = next_cast_times.get(cast_key)
            window_end = cast_time + window * 1000.0
            fight_end = fight_end_times.get((report, fight), cast_time)
            observable_end = min(window_end, next_cast_time if next_cast_time is not None else window_end, fight_end)
            by_candidate: dict[int, list[float]] = {}
            for row in by_scope_source_track.get((report, fight, cast_source, cast_track), ()):
                timestamp = float(row["timestamp"])
                if timestamp < cast_time:
                    continue
                if next_cast_time is not None and timestamp >= observable_end:
                    continue
                if next_cast_time is None and timestamp > observable_end:
                    continue
                by_candidate.setdefault(int(row["ability_game_id"]), []).append(timestamp)
            for candidate_id, timestamps in by_candidate.items():
                clustered = RotationDDPeriodicEsoLogsCandidateContinuityService._cluster_offsets(timestamps, cast_time, tolerance_ms)
                if clustered:
                    streams_by_candidate[candidate_id].append(clustered)

        summaries: list[RotationDDPeriodicEsoLogsCandidateSegmentSummary] = []
        for candidate_id in candidates:
            streams = streams_by_candidate[candidate_id]
            segment_counts: list[int] = []
            durations: list[float] = []
            occurrence_counts: list[int] = []
            inter_segment_gaps: list[float] = []
            multi_segment = 0
            resumed_5 = resumed_10 = resumed_15 = 0
            for stream in streams:
                segments = self._segments(stream, segment_gap)
                segment_counts.append(len(segments))
                if len(segments) > 1:
                    multi_segment += 1
                for start, end, occurrences in segments:
                    durations.append(end - start)
                    occurrence_counts.append(occurrences)
                for previous, following in zip(segments, segments[1:]):
                    inter_segment_gaps.append(following[0] - previous[1])
                later_starts = [segment[0] for segment in segments[1:]]
                resumed_5 += int(any(value >= 5.0 for value in later_starts))
                resumed_10 += int(any(value >= 10.0 for value in later_starts))
                resumed_15 += int(any(value >= 15.0 for value in later_starts))
            summaries.append(RotationDDPeriodicEsoLogsCandidateSegmentSummary(
                candidate_ability_id=candidate_id,
                linked_cast_count=len(streams),
                multi_segment_cast_count=multi_segment,
                median_segments_per_cast=float(median(segment_counts)) if segment_counts else None,
                maximum_segments_per_cast=max(segment_counts) if segment_counts else None,
                median_segment_duration_seconds=float(median(durations)) if durations else None,
                median_occurrences_per_segment=float(median(occurrence_counts)) if occurrence_counts else None,
                median_inter_segment_gap_seconds=float(median(inter_segment_gaps)) if inter_segment_gaps else None,
                maximum_inter_segment_gap_seconds=max(inter_segment_gaps) if inter_segment_gaps else None,
                resumed_at_or_after_5s=resumed_5,
                resumed_at_or_after_10s=resumed_10,
                resumed_at_or_after_15s=resumed_15,
            ))
        if not any(summary.linked_cast_count for summary in summaries):
            unresolved.append(f"{identity}: no censored same-source same-track candidate streams found")
        return self._report(identity, candidates, window, tolerance, segment_gap, cast_count=len(casts), summaries=tuple(summaries), unresolved=tuple(dict.fromkeys(unresolved)))

    @staticmethod
    def _segments(stream: tuple[float, ...], gap_seconds: float) -> tuple[tuple[float, float, int], ...]:
        if not stream:
            return ()
        chunks: list[list[float]] = [[stream[0]]]
        for value in stream[1:]:
            if value - chunks[-1][-1] > gap_seconds:
                chunks.append([value])
            else:
                chunks[-1].append(value)
        return tuple((chunk[0], chunk[-1], len(chunk)) for chunk in chunks)

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            rows = db.execute("SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL", (int(skill_id), int(morph))).fetchall()
        return tuple(int(row[0]) for row in rows)

    @staticmethod
    def _next_same_source_cast_times(casts: list[sqlite3.Row]) -> dict[tuple[str, int, int], float]:
        grouped: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for cast in casts:
            if cast["source_id"] is not None:
                grouped.setdefault((str(cast["report_code"]), int(cast["fight_id"]), int(cast["source_id"])), []).append(cast)
        result: dict[tuple[str, int, int], float] = {}
        for values in grouped.values():
            ordered = sorted(values, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            for current, following in zip(ordered, ordered[1:]):
                result[(str(current["report_code"]), int(current["fight_id"]), int(current["event_index"]))] = float(following["timestamp"])
        return result

    @staticmethod
    def _fight_end_times(rows: tuple[sqlite3.Row, ...]) -> dict[tuple[str, int], float]:
        result: dict[tuple[str, int], float] = {}
        for row in rows:
            key = (str(row["report_code"]), int(row["fight_id"]))
            result[key] = max(result.get(key, float("-inf")), float(row["timestamp"]))
        return result

    @classmethod
    def _matches_cast(cls, row: sqlite3.Row, identity: str, aliases: set[int]) -> bool:
        name = cls._ability_name(row)
        if name:
            return ability_entity_id(name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _ability_name(row: sqlite3.Row) -> str:
        try:
            payload = json.loads(row["raw_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            return ""
        ability = payload.get("ability") if isinstance(payload, dict) else None
        return str(ability.get("name") or "").strip() if isinstance(ability, dict) else ""

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().casefold()

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _report(skill: str, candidates: tuple[int, ...], window: float, tolerance: float, segment_gap: float, **kwargs) -> RotationDDPeriodicEsoLogsCandidateSegmentReport:
        return RotationDDPeriodicEsoLogsCandidateSegmentReport(
            skill_entity_id=skill,
            candidate_ability_ids=candidates,
            active_window_seconds=window,
            cluster_tolerance_seconds=tolerance,
            segment_gap_seconds=segment_gap,
            cast_count=kwargs.get("cast_count", 0),
            summaries=kwargs.get("summaries", ()),
            unresolved=kwargs.get("unresolved", ()),
        )


__all__ = [
    "RotationDDPeriodicEsoLogsCandidateSegmentReport",
    "RotationDDPeriodicEsoLogsCandidateSegmentService",
    "RotationDDPeriodicEsoLogsCandidateSegmentSummary",
]
