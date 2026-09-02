from __future__ import annotations

"""Bind canonical Phase 7 component timing to concrete runtime state.

The timing extractor owns source-backed cadence metadata. This layer owns only
runtime facts supplied by the caller: first occurrence, active-window end,
consumed stack count, and any separately verified within-window interval.
Missing facts remain explicit instead of being guessed.
"""

from dataclasses import dataclass
import math

from .runtime_event import PeriodicRuntimeSchedule, RuntimeEvent, schedule_periodic_runtime_events
from .skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)


@dataclass(frozen=True)
class SkillComponentRuntimeState:
    """Concrete runtime facts available for one recurring component."""

    first_occurrence_time_seconds: float | None = None
    active_end_time_seconds: float | None = None
    stack_count: int | None = None
    verified_interval_seconds: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("first_occurrence_time_seconds", self.first_occurrence_time_seconds),
            ("active_end_time_seconds", self.active_end_time_seconds),
            ("verified_interval_seconds", self.verified_interval_seconds),
        ):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be finite and non-negative when present")
        if self.verified_interval_seconds == 0:
            raise ValueError("verified_interval_seconds must be positive when present")
        if self.stack_count is not None and self.stack_count < 0:
            raise ValueError("stack_count cannot be negative")
        if (
            self.first_occurrence_time_seconds is not None
            and self.active_end_time_seconds is not None
            and self.active_end_time_seconds < self.first_occurrence_time_seconds
        ):
            raise ValueError("active_end_time_seconds cannot precede first occurrence")


@dataclass(frozen=True)
class RuntimeScheduleBindingResult:
    """Resolved schedule or explicit runtime facts still required to build one."""

    schedule: PeriodicRuntimeSchedule | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.schedule is not None and not self.unresolved


def required_runtime_inputs(
    timing: SkillComponentRuntimeTiming,
) -> tuple[str, ...]:
    """Return the concrete runtime inputs this timing shape can require."""

    required = ["first_occurrence_time_seconds"]

    if timing.bound_kind in {
        RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
        RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW,
    }:
        required.append("active_end_time_seconds")
    elif timing.bound_kind is RuntimeCadenceBoundKind.STACK_COUNT:
        required.append("stack_count")
    elif (
        timing.bound_kind is RuntimeCadenceBoundKind.FIXED_COUNT_DURATION
        and timing.interval_seconds is None
    ):
        required.append("verified_interval_seconds")

    return tuple(required)


def bind_skill_component_runtime_schedule(
    timing: SkillComponentRuntimeTiming,
    state: SkillComponentRuntimeState,
    *,
    trigger: str,
    source: str,
    target: str | None = None,
) -> RuntimeScheduleBindingResult:
    """Bind timing metadata to supplied runtime state without guessing omissions."""

    missing: list[str] = []
    for name in required_runtime_inputs(timing):
        value = getattr(state, name)
        if value is None:
            missing.append(name)
        elif name == "stack_count" and int(value) <= 0:
            missing.append(name)
        elif name == "verified_interval_seconds" and float(value) <= 0:
            missing.append(name)

    if missing:
        return RuntimeScheduleBindingResult(schedule=None, unresolved=tuple(missing))

    assert state.first_occurrence_time_seconds is not None
    schedule = timing.to_periodic_schedule(
        trigger=trigger,
        source=source,
        first_occurrence_time_seconds=state.first_occurrence_time_seconds,
        active_end_time_seconds=state.active_end_time_seconds,
        stack_count=state.stack_count,
        interval_seconds=state.verified_interval_seconds,
        target=target,
    )
    return RuntimeScheduleBindingResult(schedule=schedule)


def schedule_skill_component_runtime_events(
    timing: SkillComponentRuntimeTiming,
    state: SkillComponentRuntimeState,
    *,
    trigger: str,
    source: str,
    target: str | None = None,
    starting_sequence: int = 0,
) -> tuple[RuntimeEvent, ...] | RuntimeScheduleBindingResult:
    """Produce occurrences when fully bound; otherwise return explicit requirements."""

    binding = bind_skill_component_runtime_schedule(
        timing,
        state,
        trigger=trigger,
        source=source,
        target=target,
    )
    if not binding.resolved:
        return binding

    assert binding.schedule is not None
    return schedule_periodic_runtime_events(
        binding.schedule,
        starting_sequence=starting_sequence,
    )
