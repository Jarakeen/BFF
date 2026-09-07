from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationBarAvailabilityWindow:
    """Explicit encounter state restricting which weapon bars are usable over time."""

    name: str
    start_seconds: float
    end_seconds: float
    allowed_bars: frozenset[str]
    bar_swaps_allowed: bool = True

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("bar availability window requires a name")
        object.__setattr__(self, "name", name)

        start = float(self.start_seconds)
        end = float(self.end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("bar availability start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("bar availability end must be finite and after start")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)

        bars = frozenset(str(value or "").strip().casefold() for value in self.allowed_bars)
        if not bars or not bars.issubset({"front", "back"}):
            raise ValueError("allowed bars must contain front, back, or both")
        object.__setattr__(self, "allowed_bars", bars)
        object.__setattr__(self, "bar_swaps_allowed", bool(self.bar_swaps_allowed))

    def contains(self, time_seconds: float) -> bool:
        value = float(time_seconds)
        return self.start_seconds <= value < self.end_seconds


@dataclass(frozen=True)
class RotationBarAvailabilityViolation:
    window_name: str
    time_seconds: float
    action_kind: RotationActionKind | None
    action_name: str | None
    action_bar: str | None
    reason: str


@dataclass(frozen=True)
class RotationBarAvailabilityAssessment:
    violations: tuple[RotationBarAvailabilityViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationBarAvailabilityAssessor:
    """Audit a rotation against explicit encounter-time bar restrictions.

    The assessor does not infer mechanic timing or which bar an encounter permits.
    Those are caller-supplied facts. It only checks whether scheduled bar-dependent
    actions and swaps respect that supplied state.
    """

    def assess(
        self,
        plan: RotationPlan,
        windows: tuple[RotationBarAvailabilityWindow, ...],
    ) -> RotationBarAvailabilityAssessment:
        normalized = tuple(sorted(windows, key=lambda item: (item.start_seconds, item.end_seconds, item.name)))
        self._validate_nonoverlap(normalized)

        violations: list[RotationBarAvailabilityViolation] = []
        active_bar: str | None = None
        entered: set[str] = set()

        for action in plan.actions:
            for window in normalized:
                if window.name in entered or float(action.time_seconds) < window.start_seconds:
                    continue
                entered.add(window.name)
                if active_bar is not None and active_bar not in window.allowed_bars:
                    violations.append(
                        RotationBarAvailabilityViolation(
                            window_name=window.name,
                            time_seconds=window.start_seconds,
                            action_kind=None,
                            action_name=None,
                            action_bar=active_bar,
                            reason="active bar at restriction entry is not available",
                        )
                    )

            matching = next((window for window in normalized if window.contains(action.time_seconds)), None)
            if matching is not None:
                violation = self.action_violation(action, matching)
                if violation is not None:
                    violations.append(violation)

            if action.kind is RotationActionKind.BAR_SWAP:
                active_bar = action.bar
            elif active_bar is None and action.bar in {"front", "back"}:
                active_bar = action.bar

        # Windows beginning after the final action still need an entry-state audit.
        for window in normalized:
            if window.name in entered:
                continue
            if active_bar is not None and active_bar not in window.allowed_bars:
                violations.append(
                    RotationBarAvailabilityViolation(
                        window_name=window.name,
                        time_seconds=window.start_seconds,
                        action_kind=None,
                        action_name=None,
                        action_bar=active_bar,
                        reason="active bar at restriction entry is not available",
                    )
                )

        return RotationBarAvailabilityAssessment(tuple(violations))

    @staticmethod
    def action_violation(
        action: RotationAction,
        window: RotationBarAvailabilityWindow,
    ) -> RotationBarAvailabilityViolation | None:
        if not window.contains(action.time_seconds):
            return None

        if action.kind is RotationActionKind.BAR_SWAP:
            if not window.bar_swaps_allowed:
                return RotationBarAvailabilityViolation(
                    window_name=window.name,
                    time_seconds=action.time_seconds,
                    action_kind=action.kind,
                    action_name=action.name,
                    action_bar=action.bar,
                    reason="bar swapping is forbidden during restriction",
                )
            if action.bar not in window.allowed_bars:
                return RotationBarAvailabilityViolation(
                    window_name=window.name,
                    time_seconds=action.time_seconds,
                    action_kind=action.kind,
                    action_name=action.name,
                    action_bar=action.bar,
                    reason="bar swap destination is unavailable during restriction",
                )
            return None

        bar_dependent = {
            RotationActionKind.SKILL,
            RotationActionKind.ULTIMATE,
            RotationActionKind.LIGHT_ATTACK,
            RotationActionKind.HEAVY_ATTACK,
        }
        if action.kind in bar_dependent and action.bar not in window.allowed_bars:
            return RotationBarAvailabilityViolation(
                window_name=window.name,
                time_seconds=action.time_seconds,
                action_kind=action.kind,
                action_name=action.name,
                action_bar=action.bar,
                reason="scheduled action uses an unavailable bar",
            )
        return None

    @staticmethod
    def _validate_nonoverlap(windows: tuple[RotationBarAvailabilityWindow, ...]) -> None:
        previous: RotationBarAvailabilityWindow | None = None
        for window in windows:
            if previous is not None and window.start_seconds < previous.end_seconds:
                raise ValueError(
                    "bar availability windows cannot overlap; combine encounter state into one explicit window"
                )
            previous = window
