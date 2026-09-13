from __future__ import annotations

"""Read-only ESO Logs spatial topology evidence for Detonating Siphon.

This module interprets only the coordinate semantics documented by ESO Logs:
``sourceResources.x/y`` and ``targetResources.x/y`` are actor positions stored at
100x scale. It does not assume that the cast target is definitely the corpse, that
coordinate units are meters, or that observed hit topology alone proves a hitbox.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3
from statistics import median


@dataclass(frozen=True)
class RotationDetonatingSiphonEsoLogsSpatialTopologyReport:
    candidate_ability_id: int
    cast_count: int
    linked_event_count: int
    events_with_actor_positions: int
    events_with_cast_target_position: int
    within_radius_of_caster_count: int
    within_radius_of_cast_target_count: int
    within_radius_of_either_endpoint_count: int
    beyond_both_endpoint_radius_count: int
    median_target_to_caster_distance: float | None
    median_target_to_cast_target_distance: float | None
    median_target_to_segment_distance: float | None
    maximum_target_to_segment_distance: float | None
    cast_target_actor_count: int
    cast_target_position_stability_samples: int
    median_cast_target_position_drift: float | None
    unresolved: tuple[str, ...] = ()


class RotationDetonatingSiphonEsoLogsSpatialTopologyService:
    """Measure observed Siphon hit geometry without promoting it to canonical truth.

    ``cast_ability_ids`` are explicit observed/canonical cast event IDs supplied by the
    caller. Candidate damage rows are linked only by exact report/fight/source/cast-track.
    Cast-target coordinates are treated as a *candidate corpse anchor* and reported as
    such; the service never asserts that this actor identity is actually the corpse.
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
    ) -> RotationDetonatingSiphonEsoLogsSpatialTopologyReport:
        casts_requested = tuple(dict.fromkeys(int(value) for value in cast_ability_ids))
        candidate = int(candidate_ability_id)
        radius = float(endpoint_radius)
        if not casts_requested or any(value <= 0 for value in casts_requested):
            raise ValueError("positive Detonating Siphon cast ability ids are required")
        if candidate <= 0:
            raise ValueError("candidate_ability_id must be positive")
        if not math.isfinite(radius) or radius < 0.0:
            raise ValueError("endpoint_radius must be finite and non-negative")
        if not self.logs_database_path.is_file():
            return self._empty(candidate, f"ESO Logs database not found: {self.logs_database_path}")

        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {
                "report_code",
                "fight_id",
                "event_index",
                "timestamp",
                "event_type",
                "source_id",
                "target_id",
                "ability_game_id",
                "cast_track_id",
                "raw_json",
            }
            missing = sorted(required - columns)
            if missing:
                return self._empty(
                    candidate,
                    "log_event is missing required columns: " + ", ".join(missing),
                )
            rows = tuple(
                db.execute(
                    "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                    "target_id,ability_game_id,cast_track_id,raw_json FROM log_event "
                    "ORDER BY report_code,fight_id,source_id,timestamp,event_index"
                ).fetchall()
            )

        cast_ids = set(casts_requested)
        candidate_rows: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["ability_game_id"] is None or int(row["ability_game_id"]) != candidate:
                continue
            source_id = self._int_or_none(row["source_id"])
            track_id = self._int_or_none(row["cast_track_id"])
            if source_id is None or track_id is None:
                continue
            candidate_rows.setdefault(
                (str(row["report_code"]), int(row["fight_id"]), source_id, track_id), []
            ).append(row)

        casts = [
            row
            for row in rows
            if str(row["event_type"] or "").strip().casefold() in self._CAST_TYPES
            and row["ability_game_id"] is not None
            and int(row["ability_game_id"]) in cast_ids
            and self._int_or_none(row["source_id"]) is not None
            and self._int_or_none(row["cast_track_id"]) is not None
        ]
        if not casts:
            return self._empty(
                candidate,
                "no matching Detonating Siphon cast observations found for supplied cast ability ids",
            )

        # Prefer the most common cast event type so begin/complete/cast duplicates do not
        # make one physical cast look like several observations.
        type_counts: dict[str, int] = {}
        for row in casts:
            kind = str(row["event_type"] or "").strip().casefold()
            type_counts[kind] = type_counts.get(kind, 0) + 1
        anchor_type = max(type_counts.items(), key=lambda item: item[1])[0]
        casts = [
            row
            for row in casts
            if str(row["event_type"] or "").strip().casefold() == anchor_type
        ]

        target_to_caster: list[float] = []
        target_to_cast_target: list[float] = []
        target_to_segment: list[float] = []
        cast_target_drifts: list[float] = []
        linked_event_count = 0
        actor_position_count = 0
        cast_target_position_count = 0
        within_caster = 0
        within_cast_target = 0
        within_either = 0
        beyond_both = 0
        cast_target_actor_ids: set[int] = set()

        for cast in casts:
            source_id = int(cast["source_id"])
            track_id = int(cast["cast_track_id"])
            scope = (str(cast["report_code"]), int(cast["fight_id"]), source_id, track_id)
            events = candidate_rows.get(scope, ())
            if not events:
                continue

            cast_payload = self._payload(cast["raw_json"])
            cast_target_position = self._position(cast_payload, "targetResources")
            cast_target_id = self._int_or_none(cast["target_id"])
            if cast_target_id is not None:
                cast_target_actor_ids.add(cast_target_id)

            for event in events:
                linked_event_count += 1
                payload = self._payload(event["raw_json"])
                caster = self._position(payload, "sourceResources")
                target = self._position(payload, "targetResources")
                if caster is None or target is None:
                    continue
                actor_position_count += 1
                d_caster = self._distance(target, caster)
                target_to_caster.append(d_caster)
                inside_caster = d_caster <= radius + 1e-9
                within_caster += int(inside_caster)

                if cast_target_position is None:
                    continue
                cast_target_position_count += 1
                d_cast_target = self._distance(target, cast_target_position)
                d_segment = self._distance_to_segment(target, caster, cast_target_position)
                target_to_cast_target.append(d_cast_target)
                target_to_segment.append(d_segment)
                inside_cast_target = d_cast_target <= radius + 1e-9
                within_cast_target += int(inside_cast_target)
                within_either += int(inside_caster or inside_cast_target)
                beyond_both += int(not inside_caster and not inside_cast_target)

                # If the damage target is the same actor as the cast target, its event-time
                # position provides a conservative drift sample for the candidate anchor.
                event_target_id = self._int_or_none(event["target_id"])
                if cast_target_id is not None and event_target_id == cast_target_id:
                    cast_target_drifts.append(self._distance(target, cast_target_position))

        unresolved: list[str] = []
        if linked_event_count == 0:
            unresolved.append("no candidate damage rows linked to matching cast tracks")
        if actor_position_count == 0:
            unresolved.append("linked candidate rows expose no usable source/target x/y positions")
        if cast_target_position_count == 0:
            unresolved.append(
                "matching cast rows expose no usable targetResources x/y for candidate corpse anchor analysis"
            )

        return RotationDetonatingSiphonEsoLogsSpatialTopologyReport(
            candidate_ability_id=candidate,
            cast_count=len(casts),
            linked_event_count=linked_event_count,
            events_with_actor_positions=actor_position_count,
            events_with_cast_target_position=cast_target_position_count,
            within_radius_of_caster_count=within_caster,
            within_radius_of_cast_target_count=within_cast_target,
            within_radius_of_either_endpoint_count=within_either,
            beyond_both_endpoint_radius_count=beyond_both,
            median_target_to_caster_distance=self._median(target_to_caster),
            median_target_to_cast_target_distance=self._median(target_to_cast_target),
            median_target_to_segment_distance=self._median(target_to_segment),
            maximum_target_to_segment_distance=max(target_to_segment) if target_to_segment else None,
            cast_target_actor_count=len(cast_target_actor_ids),
            cast_target_position_stability_samples=len(cast_target_drifts),
            median_cast_target_position_drift=self._median(cast_target_drifts),
            unresolved=tuple(unresolved),
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
        text = str(raw or "").strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
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
        projection = (
            (point[0] - start[0]) * vx + (point[1] - start[1]) * vy
        ) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest = (start[0] + projection * vx, start[1] + projection * vy)
        return cls._distance(point, closest)

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        try:
            return None if value is None else int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _median(values: list[float]) -> float | None:
        return float(median(values)) if values else None

    @staticmethod
    def _empty(
        candidate_ability_id: int,
        unresolved: str,
    ) -> RotationDetonatingSiphonEsoLogsSpatialTopologyReport:
        return RotationDetonatingSiphonEsoLogsSpatialTopologyReport(
            candidate_ability_id=int(candidate_ability_id),
            cast_count=0,
            linked_event_count=0,
            events_with_actor_positions=0,
            events_with_cast_target_position=0,
            within_radius_of_caster_count=0,
            within_radius_of_cast_target_count=0,
            within_radius_of_either_endpoint_count=0,
            beyond_both_endpoint_radius_count=0,
            median_target_to_caster_distance=None,
            median_target_to_cast_target_distance=None,
            median_target_to_segment_distance=None,
            maximum_target_to_segment_distance=None,
            cast_target_actor_count=0,
            cast_target_position_stability_samples=0,
            median_cast_target_position_drift=None,
            unresolved=(unresolved,),
        )


__all__ = [
    "RotationDetonatingSiphonEsoLogsSpatialTopologyReport",
    "RotationDetonatingSiphonEsoLogsSpatialTopologyService",
]
