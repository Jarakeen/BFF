from __future__ import annotations

"""Shared deterministic runtime-event primitives for Phase 7.

This module deliberately does not create a second trigger taxonomy. Phase 6
``SkillComponentTriggerType`` values and existing ``EffectVariant.trigger``
strings remain authoritative. Runtime events only carry those trigger identities
through deterministic time ordering and bounded scheduling.
"""

from dataclasses import dataclass
import math
from typing import Iterable

from .character_build.effect_instance import EffectVariant
from .skill_component_trigger_relationship import (
    SkillComponentTriggerRelationship,
    SkillComponentTriggerType,
)


@dataclass(frozen=True)
class RuntimeEvent:
    """One observable or scheduled runtime event.

    ``trigger`` is an existing canonical trigger identity, not a new semantic
    classification. ``sequence`` is the deterministic tie-break for events at
    the same timestamp, mirroring the ordering principle used by the Phase 4
    resource timeline.
    """

    time_seconds: float
    trigger: str
    source: str
    target: str | None = None
    sequence: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError(
                f"Runtime event time must be a finite non-negative value: {self.time_seconds}"
            )
        if not str(self.trigger or "").strip():
            raise ValueError("Runtime event requires a trigger identity")
        if not str(self.source or "").strip():
            raise ValueError("Runtime event requires a source")
        if self.sequence < 0:
            raise ValueError("Runtime event sequence cannot be negative")

    @classmethod
    def for_skill_component_trigger(
        cls,
        *,
        time_seconds: float,
        trigger_type: SkillComponentTriggerType,
        source: str,
        target: str | None = None,
        sequence: int = 0,
    ) -> "RuntimeEvent":
        """Create an event using the authoritative Phase 6 trigger identity."""

        return cls(
            time_seconds=float(time_seconds),
            trigger=trigger_type.value,
            source=source,
            target=target,
            sequence=int(sequence),
        )

    @classmethod
    def for_effect_variant(
        cls,
        *,
        time_seconds: float,
        effect: EffectVariant,
        source: str | None = None,
        target: str | None = None,
        sequence: int = 0,
    ) -> "RuntimeEvent":
        """Create an event from an EffectVariant's existing named trigger."""

        if effect.trigger is None or not str(effect.trigger).strip():
            raise ValueError("EffectVariant does not define a runtime trigger")
        return cls(
            time_seconds=float(time_seconds),
            trigger=effect.trigger,
            source=source or effect.source,
            target=target,
            sequence=int(sequence),
        )


@dataclass(frozen=True)
class PeriodicRuntimeSchedule:
    """A bounded repeat schedule for one already-known runtime trigger.

    Timing is intentionally separate from trigger identity. A schedule must be
    bounded by an occurrence count, an end time, or both so Phase 7 cannot
    accidentally manufacture an infinite combat simulation.
    """

    trigger: str
    source: str
    interval_seconds: float
    start_time_seconds: float = 0.0
    occurrence_count: int | None = None
    end_time_seconds: float | None = None
    target: str | None = None

    def __post_init__(self) -> None:
        if not str(self.trigger or "").strip():
            raise ValueError("Periodic runtime schedule requires a trigger identity")
        if not str(self.source or "").strip():
            raise ValueError("Periodic runtime schedule requires a source")
        if not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0:
            raise ValueError("Periodic runtime interval must be finite and greater than zero")
        if not math.isfinite(self.start_time_seconds) or self.start_time_seconds < 0:
            raise ValueError("Periodic runtime start time must be finite and non-negative")
        if self.occurrence_count is not None and self.occurrence_count <= 0:
            raise ValueError("Periodic runtime occurrence_count must be positive when present")
        if self.end_time_seconds is not None:
            if not math.isfinite(self.end_time_seconds):
                raise ValueError("Periodic runtime end time must be finite when present")
            if self.end_time_seconds < self.start_time_seconds:
                raise ValueError("Periodic runtime end time cannot precede the start time")
        if self.occurrence_count is None and self.end_time_seconds is None:
            raise ValueError("Periodic runtime schedule must be bounded")


def runtime_event_matches_component_trigger(
    event: RuntimeEvent,
    relationship: SkillComponentTriggerRelationship,
) -> bool:
    """Whether an event satisfies a canonical Phase 6 component trigger."""

    return event.trigger == relationship.trigger_type.value


def runtime_event_matches_effect_variant(
    event: RuntimeEvent,
    effect: EffectVariant,
) -> bool:
    """Whether an event satisfies an eligible EffectVariant's named trigger."""

    return (
        effect.eligible
        and effect.trigger is not None
        and event.trigger == effect.trigger
    )


def order_runtime_events(events: Iterable[RuntimeEvent]) -> tuple[RuntimeEvent, ...]:
    """Return deterministic timestamp/sequence ordering without changing identity."""

    return tuple(sorted(events, key=lambda event: (event.time_seconds, event.sequence)))


def schedule_periodic_runtime_events(
    schedule: PeriodicRuntimeSchedule,
    *,
    starting_sequence: int = 0,
) -> tuple[RuntimeEvent, ...]:
    """Expand one bounded cadence into deterministic runtime events.

    When both bounds are present, the first bound reached wins. Event times are
    calculated from ``start + interval * index`` rather than accumulated by
    repeated floating-point addition.
    """

    if starting_sequence < 0:
        raise ValueError("starting_sequence cannot be negative")

    if schedule.occurrence_count is not None:
        max_occurrences = schedule.occurrence_count
    else:
        assert schedule.end_time_seconds is not None
        span = schedule.end_time_seconds - schedule.start_time_seconds
        max_occurrences = math.floor((span / schedule.interval_seconds) + 1e-12) + 1

    events: list[RuntimeEvent] = []
    for index in range(max_occurrences):
        time_seconds = schedule.start_time_seconds + schedule.interval_seconds * index
        if (
            schedule.end_time_seconds is not None
            and time_seconds > schedule.end_time_seconds + 1e-12
        ):
            break
        events.append(
            RuntimeEvent(
                time_seconds=time_seconds,
                trigger=schedule.trigger,
                source=schedule.source,
                target=schedule.target,
                sequence=starting_sequence + index,
            )
        )

    return tuple(events)
