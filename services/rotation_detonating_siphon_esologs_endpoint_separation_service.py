from __future__ import annotations

"""Read-only ESO Logs endpoint-separation evidence for Detonating Siphon.

This audit exists to answer one narrow question: does the imported corpus contain casts
where the caster and cast-target candidate are far enough apart to distinguish competing
area-anchor hypotheses? It interprets only ESO Logs' documented 100x actor-position scale.
It does not assert that the cast target is a corpse or that normalized coordinates are meters.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3
from statistics import median


@dataclass(frozen=True)
class RotationDetonatingSiphonEndpointSeparationThreshold:
    minimum_separation: float
    cast_count: int
    linked_event_count: int
    events_with_positions: int
    within_radius_of_caster_count: int
    within_radius_of_cast_target_count: int
    caster_only_count: int
    cast_target_only_count: int
    within_both_count: int
    beyond_both_count: int
    median_target_to_segment_distance_for_beyond_both: float | None
    maximum_target_to_segment_distance_for_beyond_both: float | None


@dataclass(frozen=True)
class RotationDetonatingSiphonEndpointSeparationReport:
    candidate_ability_id: int
    cast_count_with_positions: int
    linked_event_count: int
    median_endpoint_separation: float | None
    maximum_endpoint_separation: float | None
    separation_p90: float | None
    thresholds: tuple[RotationDetonatingSiphonEndpointSeparationThreshold, ...]
    unresolved: tuple[str, ...] = ()


class RotationDetonatingSiphonEndpointSeparationService:
    """Stratify observed Siphon hits by caster/cast-target endpoint separation.

    Only exact report/fight/source/cast-track links are used. Cast rows provide the initial
    caster and cast-target-candidate positions. Candidate damage rows provide event-time
    caster and target positions. The cast-target position remains the cast-time candidate
    anchor rather than being silently reinterpreted as a corpse.
    """

    _CAST_TYPES = {"cast", "completecast", "begincast"}
    _COORDINATE_SCALE = 100.0

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        cast_ability_ids: tuple[int, ...],
        candidate_ability_id: int = 118766,
        endpoint_radius: float = 5.0,
        minimum_separations: tuple[float, ...] = (5.0, 10.0, 15.0, 20.0),
    ) -> RotationDetonatingSiphonEndpointSeparationReport:
        cast_ids = tuple(dict.fromkeys(int(value) for value in cast_ability_ids))
        candidate = int(candidate_ability_id)
        radius = float(endpoint_radius)
        thresholds = tuple(dict.fromkeys(float(value) for value in minimum_separations))
        if not cast_ids or any(value <= 0 for value in cast_ids):
            raise ValueError("positive Detonating Siphon cast ability ids are required")
        if candidate <= 0:
            raise ValueError("candidate_ability_id must be positive")
        if not math.isfinite(radius) or radius < 0.0:
            raise ValueError("endpoint_radius must be finite and non-negative")
        if any(not math.isfinite(value) or value < 0.0 for value in thresholds):
            raise ValueError("minimum separations must be finite and non-negative")
        if not self.logs_database_path.is_file():
            return RotationDetonatingSiphonEndpointSeparationReport(
                candidate_ability_id=candidate,
                cast_count_with_positions=0,
                linked_event_count=0,
                median_endpoint_separation=None,
                maximum_endpoint_separation=None,
                separation_p90=None,
                thresholds=(),
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",),
            )

        rows = self._rows()
        cast_set = set(cast_ids)
        casts = [
            row
            for row in rows
            if str(row["event_type"] or "").strip().casefold() in self._CAST_TYPES
            and row["ability_game_id"] is not None
            and int(row["ability_game_id"]) in cast_set
            and row["source_id"] is not None
            and row["cast_track_id"] is not None
        ]
        if not casts:
            return RotationDetonatingSiphonEndpointSeparationReport(
                candidate_ability_id=candidate,
                cast_count_with_positions=0,
                linked_event_count=0,
                median_endpoint_separation=None,
                maximum_endpoint_separation=None,
                separation_p90=None,
                thresholds=(),
                unresolved=("no matching Detonating Siphon cast observations found",),
            )

        type_counts: dict[str, int] = {}
        for row in casts:
            kind = str(row["event_type"] or "").strip().casefold()
            type_counts[kind] = type_counts.get(kind, 0) + 1
        anchor_type = max(type_counts.items(), key=lambda item: item[1])[0]
        casts = [row for row in casts if str(row["event_type"] or "").strip().casefold() == anchor_type]

        candidate_by_scope: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["ability_game_id"] is None or int(row["ability_game_id"]) != candidate:
                continue
            if row["source_id"] is None or row["cast_track_id"] is None:
                continue
            scope = (
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
                int(row["cast_track_id"]),
            )
            candidate_by_scope.setdefault(scope, []).append(row)

        cast_records: list[tuple[float, tuple[sqlite3.Row, ...], tuple[float, float]]] = []
        all_linked = 0
        for cast in casts:
            payload = self._payload(cast["raw_json"])
            caster_cast = self._position(payload, "sourceResources")
            cast_target = self._position(payload, "targetResources")
            if caster_cast is None or cast_target is None:
                continue
            separation = self._distance(caster_cast, cast_target)
            scope = (
                str(cast["report_code"]),
                int(cast["fight_id"]),
                int(cast["source_id"]),
                int(cast["cast_track_id"]),
            )
            events = tuple(candidate_by_scope.get(scope, ()))
            all_linked += len(events)
            cast_records.append((separation, events, cast_target))

        separations = [record[0] for record in cast_records]
        summaries = tuple(
            self._summarize_threshold(
                cast_records=cast_records,
                minimum_separation=minimum,
                endpoint_radius=radius,
            )
            for minimum in thresholds
        )
        unresolved: list[str] = []
        if not cast_records:
            unresolved.append("matching cast rows expose no usable source/target x/y endpoint positions")
        if cast_records and max(separations) < max(thresholds, default=0.0):
            unresolved.append(
                "corpus does not contain cast endpoints separated far enough to populate every requested threshold"
            )

        return RotationDetonatingSiphonEndpointSeparationReport(
            candidate_ability_id=candidate,
            cast_count_with_positions=len(cast_records),
            linked_event_count=all_linked,
            median_endpoint_separation=self._median(separations),
            maximum_endpoint_separation=max(separations) if separations else None,
            separation_p90=self._percentile(separations, 0.90),
            thresholds=summaries,
            unresolved=tuple(unresolved),
        )

    def _summarize_threshold(
        self,
        *,
        cast_records: list[tuple[float, tuple[sqlite3.Row, ...], tuple[float, float]]],
        minimum_separation: float,
        endpoint_radius: float,
    ) -> RotationDetonatingSiphonEndpointSeparationThreshold:
        selected = [record for record in cast_records if record[0] >= minimum_separation]
        linked = 0
        positioned = 0
        in_caster = in_target = caster_only = target_only = both = neither = 0
        beyond_segment_distances: list[float] = []
        for _separation, events, cast_target in selected:
            linked += len(events)
            for event in events:
                payload = self._payload(event["raw_json"])
                caster = self._position(payload, "sourceResources")
                target = self._position(payload, "targetResources")
                if caster is None or target is None:
                    continue
                positioned += 1
                d_caster = self._distance(target, caster)
                d_target = self._distance(target, cast_target)
                inside_caster = d_caster <= endpoint_radius + 1e-9
                inside_target = d_target <= endpoint_radius + 1e-9
                in_caster += int(inside_caster)
                in_target += int(inside_target)
                if inside_caster and inside_target:
                    both += 1
                elif inside_caster:
                    caster_only += 1
                elif inside_target:
                    target_only += 1
                else:
                    neither += 1
                    beyond_segment_distances.append(
                        self._distance_to_segment(target, caster, cast_target)
                    )
        return RotationDetonatingSiphonEndpointSeparationThreshold(
            minimum_separation=float(minimum_separation),
            cast_count=len(selected),
            linked_event_count=linked,
            events_with_positions=positioned,
            within_radius_of_caster_count=in_caster,
            within_radius_of_cast_target_count=in_target,
            caster_only_count=caster_only,
            cast_target_only_count=target_only,
            within_both_count=both,
            beyond_both_count=neither,
            median_target_to_segment_distance_for_beyond_both=self._median(beyond_segment_distances),
            maximum_target_to_segment_distance_for_beyond_both=(
                max(beyond_segment_distances) if beyond_segment_distances else None
            ),
        )

    def _rows(self) -> tuple[sqlite3.Row, ...]:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {
                "report_code", "fight_id", "timestamp", "event_type", "source_id",
                "ability_game_id", "cast_track_id", "raw_json",
            }
            missing = sorted(required - columns)
            if missing:
                raise ValueError("log_event is missing required columns: " + ", ".join(missing))
            return tuple(
                db.execute(
                    "SELECT report_code,fight_id,timestamp,event_type,source_id,target_id,"
                    "ability_game_id,cast_track_id,raw_json FROM log_event "
                    "ORDER BY report_code,fight_id,source_id,timestamp"
                ).fetchall()
            )

    @classmethod
    def _position(cls, payload: dict, key: str) -> tuple[float, float] | None:
        resources = payload.get(key)
        if not isinstance(resources, dict):
            return None
        try:
            x = float(resources["x"]) / cls._COORDINATE_SCALE
            y = float(resources["y"]) / cls._COORDINATE_SCALE
        except (KeyError, TypeError, ValueError):
            return None
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        return (x, y)

    @staticmethod
    def _payload(raw: object) -> dict:
        try:
            value = json.loads(str(raw or "").strip())
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @classmethod
    def _distance_to_segment(
        cls,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        vx = end[0] - start[0]
        vy = end[1] - start[1]
        length_squared = vx * vx + vy * vy
        if length_squared <= 1e-18:
            return cls._distance(point, start)
        projection = ((point[0] - start[0]) * vx + (point[1] - start[1]) * vy) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest = (start[0] + projection * vx, start[1] + projection * vy)
        return cls._distance(point, closest)

    @staticmethod
    def _median(values: list[float]) -> float | None:
        return float(median(values)) if values else None

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return float(ordered[0])
        index = (len(ordered) - 1) * float(fraction)
        lower = math.floor(index)
        upper = math.ceil(index)
        if lower == upper:
            return float(ordered[lower])
        weight = index - lower
        return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


__all__ = [
    "RotationDetonatingSiphonEndpointSeparationReport",
    "RotationDetonatingSiphonEndpointSeparationService",
    "RotationDetonatingSiphonEndpointSeparationThreshold",
]
