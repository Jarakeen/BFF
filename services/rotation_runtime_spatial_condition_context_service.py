from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from minmax.character_build.effect_relationship import ConditionContext
from minmax.rotation_plan import RotationPlan
from minmax.runtime_event import RuntimeEvent


@dataclass(frozen=True)
class RotationRuntimeSpatialPositionWindow:
    """Explicit position evidence for one entity over one half-open runtime window."""

    entity_id: str
    start_seconds: float
    end_seconds: float
    x: float
    y: float

    def __post_init__(self) -> None:
        entity_id = str(self.entity_id or "").strip()
        if not entity_id:
            raise ValueError("runtime spatial position window requires entity_id")
        object.__setattr__(self, "entity_id", entity_id)

        start = float(self.start_seconds)
        end = float(self.end_seconds)
        x = float(self.x)
        y = float(self.y)
        if not math.isfinite(start) or start < 0.0:
            raise ValueError("runtime spatial position start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("runtime spatial position end must be finite and after start")
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("runtime spatial coordinates must be finite")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)

    def contains(self, time_seconds: float) -> bool:
        value = float(time_seconds)
        return self.start_seconds <= value < self.end_seconds


class RotationRuntimeSpatialConditionClause(Protocol):
    """One generic spatial predicate contributing to an opaque condition name."""

    def evaluate(
        self,
        *,
        time_seconds: float,
        position_at,
    ) -> bool | None: ...


@dataclass(frozen=True)
class RotationRuntimeSpatialCircleClause:
    """True when target lies within an explicit radius of one center entity."""

    center_entity_id: str
    target_entity_id: str
    maximum_distance: float

    def __post_init__(self) -> None:
        for name in ("center_entity_id", "target_entity_id"):
            value = str(getattr(self, name) or "").strip()
            if not value:
                raise ValueError(f"runtime spatial circle clause requires {name}")
            object.__setattr__(self, name, value)
        distance = float(self.maximum_distance)
        if not math.isfinite(distance) or distance < 0.0:
            raise ValueError("runtime spatial circle maximum_distance must be finite and non-negative")
        object.__setattr__(self, "maximum_distance", distance)

    def evaluate(self, *, time_seconds: float, position_at) -> bool | None:
        center = position_at(self.center_entity_id, time_seconds)
        target = position_at(self.target_entity_id, time_seconds)
        if center is None or target is None:
            return None
        distance = math.hypot(target[0] - center[0], target[1] - center[1])
        return distance <= self.maximum_distance + 1e-9


@dataclass(frozen=True)
class RotationRuntimeSpatialSegmentClause:
    """True when target lies within an explicit-width corridor over a line segment."""

    start_entity_id: str
    end_entity_id: str
    target_entity_id: str
    half_width: float

    def __post_init__(self) -> None:
        for name in ("start_entity_id", "end_entity_id", "target_entity_id"):
            value = str(getattr(self, name) or "").strip()
            if not value:
                raise ValueError(f"runtime spatial segment clause requires {name}")
            object.__setattr__(self, name, value)
        width = float(self.half_width)
        if not math.isfinite(width) or width < 0.0:
            raise ValueError("runtime spatial segment half_width must be finite and non-negative")
        object.__setattr__(self, "half_width", width)

    def evaluate(self, *, time_seconds: float, position_at) -> bool | None:
        start = position_at(self.start_entity_id, time_seconds)
        end = position_at(self.end_entity_id, time_seconds)
        target = position_at(self.target_entity_id, time_seconds)
        if start is None or end is None or target is None:
            return None

        vx = end[0] - start[0]
        vy = end[1] - start[1]
        length_squared = vx * vx + vy * vy
        if length_squared <= 1e-18:
            distance = math.hypot(target[0] - start[0], target[1] - start[1])
            return distance <= self.half_width + 1e-9

        projection = (
            (target[0] - start[0]) * vx + (target[1] - start[1]) * vy
        ) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest_x = start[0] + projection * vx
        closest_y = start[1] + projection * vy
        distance = math.hypot(target[0] - closest_x, target[1] - closest_y)
        return distance <= self.half_width + 1e-9


@dataclass(frozen=True)
class RotationRuntimeSpatialConditionRule:
    """An opaque condition whose truth is the OR of explicit spatial clauses."""

    condition: str
    clauses: tuple[RotationRuntimeSpatialConditionClause, ...]
    source: str

    def __post_init__(self) -> None:
        condition = str(self.condition or "").strip()
        source = str(self.source or "").strip()
        clauses = tuple(self.clauses)
        if not condition:
            raise ValueError("runtime spatial condition rule requires condition")
        if not clauses:
            raise ValueError("runtime spatial condition rule requires at least one clause")
        if not source:
            raise ValueError("runtime spatial condition rule requires source")
        object.__setattr__(self, "condition", condition)
        object.__setattr__(self, "clauses", clauses)
        object.__setattr__(self, "source", source)


class RotationRuntimeSpatialConditionContextService:
    """Resolve opaque ConditionContext from explicit exact-time spatial evidence.

    This service owns only generic geometry. It does not know ESO skill names, infer
    positions, invent radii, interpolate missing movement, or promote Raid Map editor
    coordinates into combat authority. A caller supplies non-overlapping position
    windows plus reviewed condition rules.

    Each condition rule uses OR semantics across its clauses. A true clause proves the
    condition even if another clause lacks evidence. If no clause is true and at least
    one clause is unknown, the entire event context is unresolved and this service
    returns ``None``. That preserves the distinction between known-false geometry and
    missing position evidence.
    """

    def __init__(
        self,
        *,
        position_windows: tuple[RotationRuntimeSpatialPositionWindow, ...],
        rules: tuple[RotationRuntimeSpatialConditionRule, ...],
    ) -> None:
        self.position_windows = tuple(position_windows)
        self.rules = tuple(rules)
        self._validate_positions(self.position_windows)
        conditions = [rule.condition for rule in self.rules]
        if len(set(conditions)) != len(conditions):
            raise ValueError("duplicate runtime spatial condition rule")

    def resolve(self, event: RuntimeEvent) -> ConditionContext | None:
        true_conditions: set[str] = set()
        for rule in self.rules:
            clause_results = tuple(
                clause.evaluate(
                    time_seconds=float(event.time_seconds),
                    position_at=self._position_at,
                )
                for clause in rule.clauses
            )
            if any(result is True for result in clause_results):
                true_conditions.add(rule.condition)
                continue
            if any(result is None for result in clause_results):
                return None
        return frozenset(true_conditions)

    def resolver_factory(self):
        def factory(_plan: RotationPlan):
            return self.resolve

        return factory

    def _position_at(
        self,
        entity_id: str,
        time_seconds: float,
    ) -> tuple[float, float] | None:
        matches = (
            window
            for window in self.position_windows
            if window.entity_id == entity_id and window.contains(time_seconds)
        )
        window = next(matches, None)
        if window is None:
            return None
        return (window.x, window.y)

    @staticmethod
    def _validate_positions(
        windows: tuple[RotationRuntimeSpatialPositionWindow, ...],
    ) -> None:
        by_entity: dict[str, list[RotationRuntimeSpatialPositionWindow]] = {}
        for window in windows:
            by_entity.setdefault(window.entity_id, []).append(window)
        for entity_id, entity_windows in by_entity.items():
            ordered = sorted(
                entity_windows,
                key=lambda item: (item.start_seconds, item.end_seconds),
            )
            previous: RotationRuntimeSpatialPositionWindow | None = None
            for window in ordered:
                if previous is not None and window.start_seconds < previous.end_seconds:
                    raise ValueError(
                        "runtime spatial position windows cannot overlap for entity "
                        f"{entity_id!r}"
                    )
                previous = window


__all__ = [
    "RotationRuntimeSpatialCircleClause",
    "RotationRuntimeSpatialConditionContextService",
    "RotationRuntimeSpatialConditionRule",
    "RotationRuntimeSpatialPositionWindow",
    "RotationRuntimeSpatialSegmentClause",
]
