from __future__ import annotations

from dataclasses import dataclass
import math

from .resource_costs import ResourceType
from .resource_timeline import ResourceTimelineEventKind, ResourceTimelineResult


@dataclass(frozen=True)
class RequiredRotationSpend:
    """One exact action-cost event that policy requires inside a resource window."""

    time_seconds: float
    source: str

    def __post_init__(self) -> None:
        time_value = float(self.time_seconds)
        if not math.isfinite(time_value) or time_value < 0:
            raise ValueError("required rotation spend time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_value)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("required rotation spend source is required")
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class RotationWindowResourceBudget:
    """Minimum entry resource needed to execute explicit required spends safely.

    The budget reuses the verified resource timeline. Only explicitly declared
    action costs count as required spending, while verified recovery/restoration
    events in the window reduce the entry requirement at the times they actually
    occur. The result is based on the worst cumulative deficit, so a late restore
    cannot conceal an earlier resource failure.
    """

    resource: ResourceType
    start_seconds: float
    end_seconds: float
    required_spends: tuple[RequiredRotationSpend, ...]
    required_spend_amount: int
    verified_gain_amount: int
    minimum_entry_amount: int
    ending_amount_from_minimum_entry: int


def derive_rotation_window_resource_budget(
    *,
    timeline: ResourceTimelineResult,
    start_seconds: float,
    end_seconds: float,
    required_spends: tuple[RequiredRotationSpend, ...],
    minimum_ending_amount: int = 0,
) -> RotationWindowResourceBudget:
    """Derive the smallest safe entry pool for one bounded required-action window.

    Window membership is ``start <= event < end``. Each required spend must
    match exactly one action-cost event in that window. Recovery and restoration
    events are included only when already present on the verified timeline.
    Discretionary or neutral action costs do not enter this budget.
    """

    start = float(start_seconds)
    end = float(end_seconds)
    if not math.isfinite(start) or start < 0:
        raise ValueError("resource budget start must be finite and non-negative")
    if not math.isfinite(end) or end <= start:
        raise ValueError("resource budget end must be finite and after start")

    ending_floor = int(minimum_ending_amount)
    if ending_floor < 0:
        raise ValueError("resource budget minimum ending amount cannot be negative")

    declarations: dict[tuple[float, str], RequiredRotationSpend] = {}
    for spend in required_spends:
        key = (float(spend.time_seconds), spend.source)
        if key in declarations:
            raise ValueError(
                f"duplicate required rotation spend: {spend.source} at {spend.time_seconds:g}s"
            )
        if spend.time_seconds < start or spend.time_seconds >= end:
            raise ValueError(
                "required rotation spend is outside resource budget window: "
                f"{spend.source} at {spend.time_seconds:g}s"
            )
        declarations[key] = spend

    action_events = tuple(
        event
        for event in timeline.events
        if start <= event.time_seconds < end
        and event.kind is ResourceTimelineEventKind.ACTION_COST
    )

    required_event_by_key = {}
    for key, spend in declarations.items():
        matches = tuple(
            event
            for event in action_events
            if event.time_seconds == spend.time_seconds and event.source == spend.source
        )
        if not matches:
            raise ValueError(
                "required rotation spend does not match an action cost in the budget window: "
                f"{spend.source} at {spend.time_seconds:g}s"
            )
        if len(matches) > 1:
            raise ValueError(
                "required rotation spend is ambiguous in the budget window: "
                f"{spend.source} at {spend.time_seconds:g}s"
            )
        required_event_by_key[key] = matches[0]

    required_event_ids = {id(event) for event in required_event_by_key.values()}
    ordered_events = tuple(
        event
        for event in timeline.events
        if start <= event.time_seconds < end
        and (
            event.kind is not ResourceTimelineEventKind.ACTION_COST
            or id(event) in required_event_ids
        )
    )

    cumulative = 0
    minimum_cumulative = 0
    required_amount = 0
    verified_gain = 0

    for event in ordered_events:
        if event.kind is ResourceTimelineEventKind.ACTION_COST:
            spent = max(0, -int(event.applied_change))
            required_amount += spent
            cumulative -= spent
        else:
            gained = max(0, int(event.applied_change))
            verified_gain += gained
            cumulative += gained
        minimum_cumulative = min(minimum_cumulative, cumulative)

    entry_for_intermediate_safety = -minimum_cumulative
    entry_for_ending_floor = max(0, ending_floor - cumulative)
    minimum_entry = max(entry_for_intermediate_safety, entry_for_ending_floor)

    return RotationWindowResourceBudget(
        resource=timeline.resource,
        start_seconds=start,
        end_seconds=end,
        required_spends=tuple(
            sorted(required_spends, key=lambda spend: (spend.time_seconds, spend.source.casefold()))
        ),
        required_spend_amount=required_amount,
        verified_gain_amount=verified_gain,
        minimum_entry_amount=minimum_entry,
        ending_amount_from_minimum_entry=minimum_entry + cumulative,
    )
