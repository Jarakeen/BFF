from __future__ import annotations

"""Canonical Phase 7 timing semantics for coefficient-local skill components.

Trigger identity remains owned by Phase 6 relationships. This module records
only repeat cadence and the source of the bound that makes a schedule finite.
It deliberately does not infer a parent ability duration or an unspoken tick
spacing from tooltip wording.
"""

from dataclasses import dataclass
from enum import Enum
import math
import re

from .runtime_event import PeriodicRuntimeSchedule


class RuntimeCadenceBoundKind(str, Enum):
    """How a recurring component obtains its finite runtime bound."""

    CALLER_ACTIVE_WINDOW = "caller_active_window"
    EXPLICIT_STATE_WINDOW = "explicit_state_window"
    FIXED_COUNT_DURATION = "fixed_count_duration"
    STACK_COUNT = "stack_count"


@dataclass(frozen=True)
class SkillComponentRuntimeTiming:
    """Source-backed cadence metadata for one recurring skill component."""

    bound_kind: RuntimeCadenceBoundKind
    evidence: str
    interval_seconds: float | None = None
    occurrence_count: int | None = None
    duration_seconds: float | None = None
    max_occurrence_count: int | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.interval_seconds is not None:
            if not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0:
                raise ValueError("runtime timing interval must be finite and positive")
        if not self.evidence:
            raise ValueError("runtime timing evidence must preserve source wording")
        if self.occurrence_count is not None and self.occurrence_count <= 0:
            raise ValueError("occurrence_count must be positive when present")
        if self.duration_seconds is not None:
            if not math.isfinite(self.duration_seconds) or self.duration_seconds <= 0:
                raise ValueError("duration_seconds must be finite and positive when present")
        if self.max_occurrence_count is not None and self.max_occurrence_count <= 0:
            raise ValueError("max_occurrence_count must be positive when present")

        if self.bound_kind is RuntimeCadenceBoundKind.FIXED_COUNT_DURATION:
            if self.occurrence_count is None or self.duration_seconds is None:
                raise ValueError("fixed-count duration timing requires count and duration")
        elif self.occurrence_count is not None or self.duration_seconds is not None:
            raise ValueError("count/duration are only valid for fixed-count duration timing")

        if self.bound_kind is RuntimeCadenceBoundKind.STACK_COUNT:
            if self.max_occurrence_count is None:
                raise ValueError("stack-count timing requires max_occurrence_count")
        elif self.max_occurrence_count is not None:
            raise ValueError("max_occurrence_count is only valid for stack-count timing")

        if self.bound_kind is not RuntimeCadenceBoundKind.FIXED_COUNT_DURATION:
            if self.interval_seconds is None:
                raise ValueError(f"{self.bound_kind.value} timing requires an explicit interval")

    def to_periodic_schedule(
        self,
        *,
        trigger: str,
        source: str,
        first_occurrence_time_seconds: float,
        active_end_time_seconds: float | None = None,
        stack_count: int | None = None,
        interval_seconds: float | None = None,
        target: str | None = None,
    ) -> PeriodicRuntimeSchedule:
        """Bind canonical timing metadata to concrete runtime state.

        The caller supplies the time of the first actual occurrence. This avoids
        guessing whether the first tick happens immediately on activation or one
        cadence interval later. ``interval_seconds`` is required only when the
        source supplied count + duration without exact within-window spacing.
        """

        resolved_interval = self.interval_seconds
        if resolved_interval is None:
            resolved_interval = interval_seconds
        if resolved_interval is None or not math.isfinite(resolved_interval) or resolved_interval <= 0:
            raise ValueError("runtime schedule requires a verified positive interval")

        if self.bound_kind is RuntimeCadenceBoundKind.FIXED_COUNT_DURATION:
            assert self.occurrence_count is not None
            assert self.duration_seconds is not None
            return PeriodicRuntimeSchedule(
                trigger=trigger,
                source=source,
                interval_seconds=resolved_interval,
                start_time_seconds=first_occurrence_time_seconds,
                occurrence_count=self.occurrence_count,
                end_time_seconds=first_occurrence_time_seconds + self.duration_seconds,
                target=target,
            )

        if self.bound_kind is RuntimeCadenceBoundKind.STACK_COUNT:
            if stack_count is None or stack_count <= 0:
                raise ValueError("stack-count timing requires a positive runtime stack_count")
            assert self.max_occurrence_count is not None
            return PeriodicRuntimeSchedule(
                trigger=trigger,
                source=source,
                interval_seconds=resolved_interval,
                start_time_seconds=first_occurrence_time_seconds,
                occurrence_count=min(int(stack_count), self.max_occurrence_count),
                target=target,
            )

        if active_end_time_seconds is None:
            raise ValueError(
                f"{self.bound_kind.value} timing requires active_end_time_seconds"
            )
        return PeriodicRuntimeSchedule(
            trigger=trigger,
            source=source,
            interval_seconds=resolved_interval,
            start_time_seconds=first_occurrence_time_seconds,
            end_time_seconds=active_end_time_seconds,
            target=target,
        )


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_FIXED_COUNT_RE = re.compile(
    r"\b(?P<count>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+times?\s+over\s+"
    r"(?P<duration>\d+(?:\.\d+)?)\s+seconds?\b",
    re.IGNORECASE,
)
_STACK_CADENCE_RE = re.compile(
    r"\bup\s+to\s+(?P<max_count>\d+)\b[^.;]{0,180}?\bevery\s+"
    r"(?P<interval>\d+(?:\.\d+)?)\s+seconds?\b[^.;]{0,120}?\bfor\s+each\s+stack\b[^.;]{0,80}?\bconsumed\b",
    re.IGNORECASE,
)
_EVERY_RE = re.compile(
    r"\b(?:once\s+)?every\s+(?P<interval>\d+(?:\.\d+)?)\s+seconds?\b",
    re.IGNORECASE,
)
_EXPLICIT_STATE_RE = re.compile(r"\bwhile\b", re.IGNORECASE)


def _parse_count(value: str) -> int:
    normalized = value.strip().casefold()
    if normalized.isdigit():
        return int(normalized)
    return _NUMBER_WORDS[normalized]


def extract_skill_component_runtime_timing(
    component_text: str,
) -> SkillComponentRuntimeTiming | None:
    """Extract only explicit recurring timing semantics from canonical wording."""

    text = " ".join(str(component_text or "").split())
    if not text:
        return None

    fixed = _FIXED_COUNT_RE.search(text)
    if fixed is not None:
        return SkillComponentRuntimeTiming(
            bound_kind=RuntimeCadenceBoundKind.FIXED_COUNT_DURATION,
            occurrence_count=_parse_count(fixed.group("count")),
            duration_seconds=float(fixed.group("duration")),
            evidence=fixed.group(0),
        )

    stack = _STACK_CADENCE_RE.search(text)
    if stack is not None:
        return SkillComponentRuntimeTiming(
            interval_seconds=float(stack.group("interval")),
            bound_kind=RuntimeCadenceBoundKind.STACK_COUNT,
            max_occurrence_count=int(stack.group("max_count")),
            evidence=stack.group(0),
        )

    every = _EVERY_RE.search(text)
    if every is None:
        return None

    return SkillComponentRuntimeTiming(
        interval_seconds=float(every.group("interval")),
        bound_kind=(
            RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW
            if _EXPLICIT_STATE_RE.search(text)
            else RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW
        ),
        evidence=every.group(0),
    )
