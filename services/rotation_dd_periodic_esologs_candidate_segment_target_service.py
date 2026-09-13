from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateSegmentTargetSummary:
    candidate_ability_id: int
    linked_cast_count: int
    multi_segment_cast_count: int
    later_segment_count: int
    repeat_only_later_segment_count: int
    new_only_later_segment_count: int
    mixed_later_segment_count: int
    unknown_target_later_segment_count: int
    median_targets_first_segment: float | None
    median_targets_later_segment: float | None
    repeat_or_mixed_start_at_or_after_5s: int
    repeat_or_mixed_start_at_or_after_10s: int
    repeat_or_mixed_start_at_or_after_15s: int
    new_only_start_at_or_after_5s: int
    new_only_start_at_or_after_10s: int
    new_only_start_at_or_after_15s: int


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateSegmentTargetReport:
    skill_entity_id: str
    candidate_ability_ids: tuple[int, ...]
    active_window_seconds: float
    cluster_tolerance_seconds: float
    segment_gap_seconds: float
    cast_count: int
    summaries: tuple[RotationDDPeriodicEsoLogsCandidateSegmentTargetSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsCandidateSegmentTargetService:
    """Observe whether later candidate segments revisit old targets or introduce new ones.

    Candidate numeric IDs remain observational evidence handles only. Same-source,
    same-cast-track events are censored at the next same-source cast, reviewed active
    window end, or imported fight end. Near-simultaneous events are grouped into one
    occurrence while preserving the union of target ids seen in that occurrence. A new
    segment begins only when the gap between clustered occurrences exceeds the reviewed
    segment gap. Later segments are compared with the union of targets observed in all
    prior segments on that cast track.
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
    ) -> RotationDDPeriodicEsoLogsCandidateSegmentTargetReport:
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
            required = {
                "report_code", "fight_id", "event_index", "timestamp", "event_type",
                "source_id", "target_id", "ability_game_id", "cast_track_id", "raw_json",
            }
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
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,target_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall())

        casts = [
            row for row in rows
            if self._event_type(row) in self._CAST_TYPES
            and self._matches_cast(row, identity, aliases)
            and (source_id is None or self._int_or_none(row["source_id"]) == int(source_id))
        ]
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

        streams_by_candidate: dict[int, list[tuple[tuple[float, frozenset[int]], ...]]] = {candidate: [] for candidate in candidates}
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
            by_candidate: dict[int, list[tuple[float, int | None]]] = {}
            for row in by_scope_source_track.get((report, fight, cast_source, cast_track), ()):
                timestamp = float(row["timestamp"])
                if timestamp < cast_time:
                    continue
                if next_cast_time is not None and timestamp >= observable_end:
                    continue
                if next_cast_time is None and timestamp > observable_end:
                    continue
                by_candidate.setdefault(int(row["ability_game_id"]), []).append((timestamp, self._int_or_none(row["target_id"])))
            for candidate_id, events in by_candidate.items():
                clustered = self._cluster_occurrences(events, cast_time, tolerance_ms)
                if clustered:
                    streams_by_candidate[candidate_id].append(clustered)

        summaries: list[RotationDDPeriodicEsoLogsCandidateSegmentTargetSummary] = []
        for candidate_id in candidates:
            streams = streams_by_candidate[candidate_id]
            multi_segment_casts = 0
            later_segment_count = 0
            repeat_only = new_only = mixed = unknown = 0
            first_target_counts: list[int] = []
            later_target_counts: list[int] = []
            repeat_or_mixed_5 = repeat_or_mixed_10 = repeat_or_mixed_15 = 0
            new_only_5 = new_only_10 = new_only_15 = 0
            for stream in streams:
                segments = self._segments(stream, segment_gap)
                if not segments:
                    continue
                first_target_counts.append(len(segments[0][2]))
                if len(segments) > 1:
                    multi_segment_casts += 1
                prior_targets = set(segments[0][2])
                cast_repeat_starts: list[float] = []
                cast_new_starts: list[float] = []
                for start, _end, targets in segments[1:]:
                    later_segment_count += 1
                    later_target_counts.append(len(targets))
                    target_set = set(targets)
                    if not target_set:
                        unknown += 1
                    else:
                        repeated = bool(target_set & prior_targets)
                        introduced = bool(target_set - prior_targets)
                        if repeated and introduced:
                            mixed += 1
                            cast_repeat_starts.append(start)
                        elif repeated:
                            repeat_only += 1
                            cast_repeat_starts.append(start)
                        else:
                            new_only += 1
                            cast_new_starts.append(start)
                    prior_targets.update(target_set)
                repeat_or_mixed_5 += int(any(value >= 5.0 for value in cast_repeat_starts))
                repeat_or_mixed_10 += int(any(value >= 10.0 for value in cast_repeat_starts))
                repeat_or_mixed_15 += int(any(value >= 15.0 for value in cast_repeat_starts))
                new_only_5 += int(any(value >= 5.0 for value in cast_new_starts))
                new_only_10 += int(any(value >= 10.0 for value in cast_new_starts))
                new_only_15 += int(any(value >= 15.0 for value in cast_new_starts))
            summaries.append(RotationDDPeriodicEsoLogsCandidateSegmentTargetSummary(
                candidate_ability_id=candidate_id,
                linked_cast_count=len(streams),
                multi_segment_cast_count=multi_segment_casts,
                later_segment_count=later_segment_count,
                repeat_only_later_segment_count=repeat_only,
                new_only_later_segment_count=new_only,
                mixed_later_segment_count=mixed,
                unknown_target_later_segment_count=unknown,
                median_targets_first_segment=float(median(first_target_counts)) if first_target_counts else None,
                median_targets_later_segment=float(median(later_target_counts)) if later_target_counts else None,
                repeat_or_mixed_start_at_or_after_5s=repeat_or_mixed_5,
                repeat_or_mixed_start_at_or_after_10s=repeat_or_mixed_10,
                repeat_or_mixed_start_at_or_after_15s=repeat_or_mixed_15,
                new_only_start_at_or_after_5s=new_only_5,
                new_only_start_at_or_after_10s=new_only_10,
                new_only_start_at_or_after_15s=new_only_15,
            ))
        if not any(summary.linked_cast_count for summary in summaries):
            unresolved.append(f"{identity}: no censored same-source same-track candidate streams found")
        return self._report(identity, candidates, window, tolerance, segment_gap, cast_count=len(casts), summaries=tuple(summaries), unresolved=tuple(dict.fromkeys(unresolved)))

    @staticmethod
    def _cluster_occurrences(
        events: list[tuple[float, int | None]], cast_time: float, tolerance_ms: float
    ) -> tuple[tuple[float, frozenset[int]], ...]:
        ordered = sorted((float(timestamp), target) for timestamp, target in events)
        if not ordered:
            return ()
        clusters: list[list[tuple[float, int | None]]] = [[ordered[0]]]
        for event in ordered[1:]:
            if event[0] - clusters[-1][-1][0] <= tolerance_ms:
                clusters[-1].append(event)
            else:
                clusters.append([event])
        result: list[tuple[float, frozenset[int]]] = []
        for cluster in clusters:
            targets = frozenset(target for _timestamp, target in cluster if target is not None)
            result.append(((cluster[0][0] - cast_time) / 1000.0, targets))
        return tuple(result)

    @staticmethod
    def _segments(
        occurrences: tuple[tuple[float, frozenset[int]], ...], gap_seconds: float
    ) -> tuple[tuple[float, float, frozenset[int]], ...]:
        if not occurrences:
            return ()
        chunks: list[list[tuple[float, frozenset[int]]]] = [[occurrences[0]]]
        for occurrence in occurrences[1:]:
            if occurrence[0] - chunks[-1][-1][0] > gap_seconds:
                chunks.append([occurrence])
            else:
                chunks[-1].append(occurrence)
        result = []
        for chunk in chunks:
            targets: set[int] = set()
            for _offset, target_ids in chunk:
                targets.update(target_ids)
            result.append((chunk[0][0], chunk[-1][0], frozenset(targets)))
        return tuple(result)

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            rows = db.execute(
                "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
                (int(skill_id), int(morph)),
            ).fetchall()
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
    def _report(skill: str, candidates: tuple[int, ...], window: float, tolerance: float, segment_gap: float, **kwargs) -> RotationDDPeriodicEsoLogsCandidateSegmentTargetReport:
        return RotationDDPeriodicEsoLogsCandidateSegmentTargetReport(
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
    "RotationDDPeriodicEsoLogsCandidateSegmentTargetReport",
    "RotationDDPeriodicEsoLogsCandidateSegmentTargetService",
    "RotationDDPeriodicEsoLogsCandidateSegmentTargetSummary",
]
