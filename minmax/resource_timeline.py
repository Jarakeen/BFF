from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .final_action_cost import FinalActionCost
from .recovery_timing import ScheduledRecoveryTick, apply_scheduled_recovery_tick
from .resource_costs import ResourceType
from .resource_state import StaticResourcePool
from .restoration_events import ResourceRestorationEvent, apply_resource_restoration_event


class ResourceTimelineEventKind(str, Enum):
    ACTION_COST = "action_cost"
    RECOVERY_TICK = "recovery_tick"
    RESTORATION = "restoration"


_EVENT_PRIORITY = {
    ResourceTimelineEventKind.ACTION_COST: 0,
    ResourceTimelineEventKind.RECOVERY_TICK: 1,
    ResourceTimelineEventKind.RESTORATION: 2,
}


@dataclass(frozen=True)
class ResourceCostEvent:
    """One resolved action cost placed on the resource timeline."""

    time_seconds: float
    resource: ResourceType
    amount: int
    source: str

    def __post_init__(self) -> None:
        if self.time_seconds < 0:
            raise ValueError(f"Resource cost event time cannot be negative: {self.time_seconds}")
        if self.amount < 0:
            raise ValueError(f"Resource cost amount cannot be negative: {self.amount}")
        if not str(self.source or "").strip():
            raise ValueError("Resource cost event requires a source")


@dataclass(frozen=True)
class AppliedResourceTimelineEvent:
    """One auditable state transition on a single-resource timeline."""

    time_seconds: float
    kind: ResourceTimelineEventKind
    source: str
    before: int
    attempted_change: int
    applied_change: int
    after: int
    shortfall: int = 0
    wasted_restore: int = 0


@dataclass(frozen=True)
class ResourceTimelineResult:
    """Deterministic event history for one primary resource pool."""

    resource: ResourceType
    starting_amount: int
    ending_amount: int
    events: tuple[AppliedResourceTimelineEvent, ...]

    @property
    def total_shortfall(self) -> int:
        return sum(event.shortfall for event in self.events)

    @property
    def has_shortfall(self) -> bool:
        return self.total_shortfall > 0


def create_action_cost_events(
    *,
    time_seconds: float,
    final_cost: FinalActionCost,
    source: str,
) -> tuple[ResourceCostEvent, ...]:
    """Place each resolved resource side of one action onto the timeline."""

    return tuple(
        ResourceCostEvent(
            time_seconds=float(time_seconds),
            resource=resource_cost.resource,
            amount=int(resource_cost.final_amount),
            source=source,
        )
        for resource_cost in final_cost.resource_costs
    )


def run_resource_timeline(
    pool: StaticResourcePool,
    *,
    starting_amount: int,
    cost_events: tuple[ResourceCostEvent, ...] = (),
    recovery_ticks: tuple[ScheduledRecoveryTick, ...] = (),
    restoration_events: tuple[ResourceRestorationEvent, ...] = (),
) -> ResourceTimelineResult:
    """Apply verified Phase 4 resource events in deterministic time order.

    This first 4E timeline intentionally models one resource pool at a time.
    Events at the same timestamp use the established sustain-flow ordering:

        action cost -> recovery tick -> restoration event

    A planned action whose cost exceeds the current pool records a shortfall and
    floors the resource at zero. The later 4F sustain-result layer will interpret
    that shortfall as a failure point; this timeline only records state changes.
    """

    current = int(starting_amount)
    if current < 0 or current > pool.maximum:
        raise ValueError(
            f"Starting {pool.resource.value} must be between 0 and {pool.maximum}: {current}"
        )

    queued: list[tuple[float, int, int, ResourceTimelineEventKind, object]] = []
    sequence = 0

    for event in cost_events:
        if event.resource is not pool.resource:
            raise ValueError(
                f"Cost event resource does not match pool: {event.resource.value} != {pool.resource.value}"
            )
        queued.append(
            (event.time_seconds, _EVENT_PRIORITY[ResourceTimelineEventKind.ACTION_COST], sequence,
             ResourceTimelineEventKind.ACTION_COST, event)
        )
        sequence += 1

    for event in recovery_ticks:
        if event.tick.resource is not pool.resource:
            raise ValueError(
                "Recovery tick resource does not match pool: "
                f"{event.tick.resource.value} != {pool.resource.value}"
            )
        queued.append(
            (event.time_seconds, _EVENT_PRIORITY[ResourceTimelineEventKind.RECOVERY_TICK], sequence,
             ResourceTimelineEventKind.RECOVERY_TICK, event)
        )
        sequence += 1

    for event in restoration_events:
        if event.resource is not pool.resource:
            raise ValueError(
                "Restoration event resource does not match pool: "
                f"{event.resource.value} != {pool.resource.value}"
            )
        queued.append(
            (event.time_seconds, _EVENT_PRIORITY[ResourceTimelineEventKind.RESTORATION], sequence,
             ResourceTimelineEventKind.RESTORATION, event)
        )
        sequence += 1

    applied: list[AppliedResourceTimelineEvent] = []
    for _time, _priority, _sequence, kind, raw_event in sorted(queued, key=lambda item: item[:3]):
        before = current

        if kind is ResourceTimelineEventKind.ACTION_COST:
            event = raw_event
            assert isinstance(event, ResourceCostEvent)
            attempted = int(event.amount)
            spent = min(current, attempted)
            shortfall = attempted - spent
            current -= spent
            applied.append(
                AppliedResourceTimelineEvent(
                    time_seconds=event.time_seconds,
                    kind=kind,
                    source=event.source,
                    before=before,
                    attempted_change=-attempted,
                    applied_change=-spent,
                    after=current,
                    shortfall=shortfall,
                )
            )
            continue

        if kind is ResourceTimelineEventKind.RECOVERY_TICK:
            event = raw_event
            assert isinstance(event, ScheduledRecoveryTick)
            result = apply_scheduled_recovery_tick(pool, current, event)
            current = result.after
            applied.append(
                AppliedResourceTimelineEvent(
                    time_seconds=event.time_seconds,
                    kind=kind,
                    source="In-combat recovery tick",
                    before=before,
                    attempted_change=result.attempted_restore,
                    applied_change=result.applied_restore,
                    after=current,
                    wasted_restore=result.attempted_restore - result.applied_restore,
                )
            )
            continue

        event = raw_event
        assert isinstance(event, ResourceRestorationEvent)
        result = apply_resource_restoration_event(pool, current_amount=current, event=event)
        current = result.resulting_amount
        applied.append(
            AppliedResourceTimelineEvent(
                time_seconds=event.time_seconds,
                kind=kind,
                source=event.source,
                before=before,
                attempted_change=result.attempted_restore,
                applied_change=result.applied_restore,
                after=current,
                wasted_restore=result.wasted_restore,
            )
        )

    return ResourceTimelineResult(
        resource=pool.resource,
        starting_amount=int(starting_amount),
        ending_amount=current,
        events=tuple(applied),
    )
