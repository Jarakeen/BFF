from __future__ import annotations

from dataclasses import dataclass

from .resource_costs import ResourceType
from .resource_state import StaticResourcePool


@dataclass(frozen=True)
class ResourceRestorationEvent:
    """One explicit resource restoration event on the Phase 4 timeline.

    This contract represents event identity only: what restores, how much,
    when, and from which source. It does not infer proc conditions, cooldowns,
    heavy-attack completion, potion use, or external-provider uptime.
    """

    time_seconds: float
    resource: ResourceType
    amount: int
    source: str

    def __post_init__(self) -> None:
        if self.time_seconds < 0:
            raise ValueError(
                f"Resource restoration event time cannot be negative: {self.time_seconds}"
            )
        if self.amount < 0:
            raise ValueError(
                f"Resource restoration amount cannot be negative: {self.amount}"
            )
        if not str(self.source or "").strip():
            raise ValueError("Resource restoration event requires a source")


@dataclass(frozen=True)
class AppliedResourceRestoration:
    """Result of applying one restoration event to one resource pool."""

    event: ResourceRestorationEvent
    previous_amount: int
    attempted_restore: int
    applied_restore: int
    resulting_amount: int
    wasted_restore: int


def apply_resource_restoration_event(
    pool: StaticResourcePool,
    *,
    current_amount: int,
    event: ResourceRestorationEvent,
) -> AppliedResourceRestoration:
    """Apply one flat restoration event with deterministic maximum clamping."""

    current = int(current_amount)
    if current < 0 or current > pool.maximum:
        raise ValueError(
            f"Current {pool.resource.value} must be between 0 and {pool.maximum}: {current}"
        )
    if event.resource is not pool.resource:
        raise ValueError(
            "Restoration event resource does not match pool: "
            f"event={event.resource.value}, pool={pool.resource.value}"
        )

    attempted = int(event.amount)
    resulting = min(pool.maximum, current + attempted)
    applied = resulting - current
    wasted = attempted - applied
    return AppliedResourceRestoration(
        event=event,
        previous_amount=current,
        attempted_restore=attempted,
        applied_restore=applied,
        resulting_amount=resulting,
        wasted_restore=wasted,
    )
