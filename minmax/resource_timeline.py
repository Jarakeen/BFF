from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .final_action_cost import FinalActionCost
from .recovery_timing import ScheduledRecoveryTick, apply_scheduled_recovery_tick
from .resource_costs import ResourceType
from .resource_state import StaticResourcePool
from .restoration_events import ResourceRestorationEvent, apply_resource_restoration_event


class ResourceTimelineEventKind(str, Enum):
    RESOURCE_MAXIMUM = "resource_maximum"
    ACTION_COST = "action_cost"
    RECOVERY_TICK = "recovery_tick"
    RESTORATION = "restoration"


_EVENT_PRIORITY = {
    ResourceTimelineEventKind.RESOURCE_MAXIMUM: 0,
    ResourceTimelineEventKind.ACTION_COST: 1,
    ResourceTimelineEventKind.RECOVERY_TICK: 2,
    ResourceTimelineEventKind.RESTORATION: 3,
}


@dataclass(frozen=True)
class ResourceMaximumEvent:
    """One verified change to the active maximum of a primary resource pool."""

    time_seconds: float
    resource: ResourceType
    maximum: int
    source: str

    def __post_init__(self) -> None:
        if self.time_seconds < 0:
            raise ValueError(
                f"Resource maximum event time cannot be negative: {self.time_seconds}"
            )
        if self.amount_is_invalid:
            raise ValueError(f"Resource maximum cannot be negative: {self.maximum}")
        if not str(self.source or "").strip():
            raise ValueError("Resource maximum event requires a source")

    @property
    def amount_is_invalid(self) -> bool:
        return int(self.maximum) < 0


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
    maximum_before: int | None = None
    maximum_after: int | None = None
    clipped_amount: int = 0


@dataclass(frozen=True)
class ResourceTimelineResult:
    """Deterministic event history for one primary resource pool."""

    resource: ResourceType
    starting_amount: int
    ending_amount: int
    events: tuple[AppliedResourceTimelineEvent, ...]
    ending_maximum: int | None = None

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
    maximum_events: tuple[ResourceMaximumEvent, ...] = (),
) -> ResourceTimelineResult:
    """Apply verified Phase 4 resource events in deterministic time order.

    This timeline models one primary resource at a time. Callers may optionally
    supply verified maximum-resource changes, such as a bar swap that activates a
    different canonical maximum. At the same timestamp the active ceiling changes
    before costs, recovery, and restoration so destination-bar state governs later
    resource consequences at that timestamp::

        resource maximum -> action cost -> recovery tick -> restoration event

    Lowering the maximum clips the current amount to the new ceiling and records the
    clipped amount explicitly. Raising the maximum never grants resource by itself.
    Existing callers that omit ``maximum_events`` retain the historical static-pool
    behavior.
    """

    current = int(starting_amount)
    current_maximum = int(pool.maximum)
    if current < 0 or current > current_maximum:
        raise ValueError(
            f"Starting {pool.resource.value} must be between 0 and {current_maximum}: {current}"
        )

    queued: list[tuple[float, int, int, ResourceTimelineEventKind, object]] = []
    sequence = 0

    for event in maximum_events:
        if event.resource is not pool.resource:
            raise ValueError(
                "Resource maximum event does not match pool: "
                f"{event.resource.value} != {pool.resource.value}"
            )
        queued.append(
            (
                event.time_seconds,
                _EVENT_PRIORITY[ResourceTimelineEventKind.RESOURCE_MAXIMUM],
                sequence,
                ResourceTimelineEventKind.RESOURCE_MAXIMUM,
                event,
            )
        )
        sequence += 1

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
        maximum_before = current_maximum

        if kind is ResourceTimelineEventKind.RESOURCE_MAXIMUM:
            event = raw_event
            assert isinstance(event, ResourceMaximumEvent)
            current_maximum = int(event.maximum)
            clipped = max(0, current - current_maximum)
            current = min(current, current_maximum)
            applied.append(
                AppliedResourceTimelineEvent(
                    time_seconds=event.time_seconds,
                    kind=kind,
                    source=event.source,
                    before=before,
                    attempted_change=0,
                    applied_change=current - before,
                    after=current,
                    maximum_before=maximum_before,
                    maximum_after=current_maximum,
                    clipped_amount=clipped,
                )
            )
            continue

        active_pool = StaticResourcePool(
            resource=pool.resource,
            maximum=current_maximum,
            displayed_recovery=pool.displayed_recovery,
        )

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
                    maximum_before=maximum_before,
                    maximum_after=current_maximum,
                )
            )
            continue

        if kind is ResourceTimelineEventKind.RECOVERY_TICK:
            event = raw_event
            assert isinstance(event, ScheduledRecoveryTick)
            result = apply_scheduled_recovery_tick(active_pool, current, event)
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
                    maximum_before=maximum_before,
                    maximum_after=current_maximum,
                )
            )
            continue

        event = raw_event
        assert isinstance(event, ResourceRestorationEvent)
        result = apply_resource_restoration_event(
            active_pool,
            current_amount=current,
            event=event,
        )
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
                maximum_before=maximum_before,
                maximum_after=current_maximum,
            )
        )

    return ResourceTimelineResult(
        resource=pool.resource,
        starting_amount=int(starting_amount),
        ending_amount=current,
        events=tuple(applied),
        ending_maximum=current_maximum,
    )
