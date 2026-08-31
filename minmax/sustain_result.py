from __future__ import annotations

from dataclasses import dataclass

from .resource_costs import ResourceType
from .resource_timeline import ResourceTimelineEventKind, ResourceTimelineResult


@dataclass(frozen=True)
class SustainFailure:
    """First resource shortfall encountered on a deterministic timeline."""

    time_seconds: float
    source: str
    shortfall: int
    resource_before: int
    attempted_cost: int


@dataclass(frozen=True)
class SustainResult:
    """Phase 4 interpretation of one deterministic resource timeline.

    This layer does not recalculate combat math. It summarizes the event trace
    produced by ``run_resource_timeline`` into the quantities needed by later
    build comparison and optimization code.
    """

    resource: ResourceType
    sustains: bool
    starting_amount: int
    ending_amount: int
    ending_margin: int
    minimum_amount: int
    first_failure: SustainFailure | None
    total_cost_attempted: int
    total_cost_paid: int
    total_restoration_applied: int
    total_restoration_wasted: int


def summarize_sustain(timeline: ResourceTimelineResult) -> SustainResult:
    """Summarize one resource timeline without changing its event semantics."""

    minimum = int(timeline.starting_amount)
    total_cost_attempted = 0
    total_cost_paid = 0
    total_restoration_applied = 0
    total_restoration_wasted = 0
    first_failure: SustainFailure | None = None

    for event in timeline.events:
        minimum = min(minimum, int(event.before), int(event.after))

        if event.kind is ResourceTimelineEventKind.ACTION_COST:
            attempted_cost = max(0, -int(event.attempted_change))
            paid = max(0, -int(event.applied_change))
            total_cost_attempted += attempted_cost
            total_cost_paid += paid

            if event.shortfall > 0 and first_failure is None:
                first_failure = SustainFailure(
                    time_seconds=float(event.time_seconds),
                    source=event.source,
                    shortfall=int(event.shortfall),
                    resource_before=int(event.before),
                    attempted_cost=attempted_cost,
                )
            continue

        total_restoration_applied += max(0, int(event.applied_change))
        total_restoration_wasted += max(0, int(event.wasted_restore))

    return SustainResult(
        resource=timeline.resource,
        sustains=first_failure is None,
        starting_amount=int(timeline.starting_amount),
        ending_amount=int(timeline.ending_amount),
        ending_margin=int(timeline.ending_amount),
        minimum_amount=minimum,
        first_failure=first_failure,
        total_cost_attempted=total_cost_attempted,
        total_cost_paid=total_cost_paid,
        total_restoration_applied=total_restoration_applied,
        total_restoration_wasted=total_restoration_wasted,
    )
