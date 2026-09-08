from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationActionKind, RotationPlan


_SUPPORTED_KINDS = frozenset({
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
})


@dataclass(frozen=True)
class RotationActionRangeRequirement:
    """Caller-supplied canonical range limits for one named skill or ultimate."""

    action_name: str
    minimum_range: float = 0.0
    maximum_range: float | None = None
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None

    def __post_init__(self) -> None:
        name = str(self.action_name or "").strip()
        if not name:
            raise ValueError("rotation range requirement needs action_name")
        object.__setattr__(self, "action_name", name)

        minimum = float(self.minimum_range)
        if not math.isfinite(minimum) or minimum < 0:
            raise ValueError("rotation minimum range must be finite and non-negative")
        object.__setattr__(self, "minimum_range", minimum)

        if self.maximum_range is not None:
            maximum = float(self.maximum_range)
            if not math.isfinite(maximum) or maximum < minimum:
                raise ValueError(
                    "rotation maximum range must be finite and at least minimum range"
                )
            object.__setattr__(self, "maximum_range", maximum)

        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation range action kind: {self.action_kind!r}"
            ) from exc
        if kind not in _SUPPORTED_KINDS:
            raise ValueError("rotation range requirements support skill or ultimate actions")
        object.__setattr__(self, "action_kind", kind)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation range requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTargetDistanceWindow:
    """Explicit encounter-time distance to the target of scheduled actions."""

    name: str
    start_seconds: float
    end_seconds: float
    distance: float

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("rotation target-distance window requires a name")
        object.__setattr__(self, "name", name)

        start = float(self.start_seconds)
        end = float(self.end_seconds)
        distance = float(self.distance)
        if not math.isfinite(start) or start < 0:
            raise ValueError("target-distance start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("target-distance end must be finite and after start")
        if not math.isfinite(distance) or distance < 0:
            raise ValueError("target distance must be finite and non-negative")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(self, "distance", distance)

    def contains(self, time_seconds: float) -> bool:
        value = float(time_seconds)
        return self.start_seconds <= value < self.end_seconds


@dataclass(frozen=True)
class RotationActionRangeViolation:
    requirement: RotationActionRangeRequirement
    window_name: str
    time_seconds: float
    distance: float
    minimum_range: float
    maximum_range: float | None

    @property
    def reason(self) -> str:
        if self.distance < self.minimum_range:
            return "target is inside the action's minimum range"
        return "target is outside the action's maximum range"


@dataclass(frozen=True)
class RotationActionRangeAssessment:
    violations: tuple[RotationActionRangeViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActionRangeAssessor:
    """Audit action range against explicit encounter target-distance evidence.

    Skill limits and encounter distance stay separate. The caller supplies both;
    this layer does not infer positioning, target identity, or movement from role,
    encounter name, or action name. Distance values must use the same canonical
    unit as the supplied skill range evidence.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirements: tuple[RotationActionRangeRequirement, ...],
        windows: tuple[RotationTargetDistanceWindow, ...],
    ) -> RotationActionRangeAssessment:
        self._validate_unique(requirements)
        normalized_windows = tuple(
            sorted(windows, key=lambda item: (item.start_seconds, item.end_seconds, item.name))
        )
        self._validate_nonoverlap(normalized_windows)
        violations: list[RotationActionRangeViolation] = []

        for requirement in requirements:
            target = requirement.action_name.casefold()
            for action in plan.actions:
                if action.kind is not requirement.action_kind:
                    continue
                if not action.name or str(action.name).casefold() != target:
                    continue
                if requirement.bar is not None and action.bar != requirement.bar:
                    continue
                window = next(
                    (item for item in normalized_windows if item.contains(action.time_seconds)),
                    None,
                )
                if window is None:
                    continue

                distance = float(window.distance)
                below_minimum = distance + 1e-9 < requirement.minimum_range
                above_maximum = (
                    requirement.maximum_range is not None
                    and distance - 1e-9 > requirement.maximum_range
                )
                if below_minimum or above_maximum:
                    violations.append(
                        RotationActionRangeViolation(
                            requirement=requirement,
                            window_name=window.name,
                            time_seconds=float(action.time_seconds),
                            distance=distance,
                            minimum_range=requirement.minimum_range,
                            maximum_range=requirement.maximum_range,
                        )
                    )

        return RotationActionRangeAssessment(tuple(violations))

    @staticmethod
    def _validate_unique(
        requirements: tuple[RotationActionRangeRequirement, ...],
    ) -> None:
        seen: set[tuple[RotationActionKind, str, str | None]] = set()
        for requirement in requirements:
            key = (
                requirement.action_kind,
                requirement.action_name.casefold(),
                requirement.bar,
            )
            if key in seen:
                raise ValueError(
                    "duplicate rotation range requirement for "
                    f"{requirement.action_name!r}"
                )
            seen.add(key)

    @staticmethod
    def _validate_nonoverlap(
        windows: tuple[RotationTargetDistanceWindow, ...],
    ) -> None:
        previous: RotationTargetDistanceWindow | None = None
        for window in windows:
            if previous is not None and window.start_seconds < previous.end_seconds:
                raise ValueError(
                    "target-distance windows cannot overlap; combine encounter state into one explicit window"
                )
            previous = window


__all__ = [
    "RotationActionRangeAssessment",
    "RotationActionRangeAssessor",
    "RotationActionRangeRequirement",
    "RotationActionRangeViolation",
    "RotationTargetDistanceWindow",
]
