from __future__ import annotations

from dataclasses import dataclass
import math

from .resource_costs import ResourceType
from .resource_timeline import ResourceTimelineResult
from .rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    resource_amount_before,
)


@dataclass(frozen=True)
class HealerRecoveryHeavyPressure:
    """Resource evidence for whether a healer recovery heavy is worth considering.

    This is intentionally not a scheduling decision. It answers only whether the
    resource state creates recovery pressure at one exact decision point. Channel
    safety, active bar/weapon, refresh collisions, and higher-priority actions are
    still evaluated by the existing heavy-opportunity and WAIT-decision layers.
    """

    resource: ResourceType
    time_seconds: float
    current_amount: int
    maximum_amount: int
    resource_fraction: float
    trigger_fraction: float
    reserve_shortfall: int
    recommended: bool
    reason: str


def evaluate_healer_recovery_heavy_pressure(
    *,
    timeline: ResourceTimelineResult,
    time_seconds: float,
    maximum_amount: int,
    trigger_fraction: float,
    reserve_assessment: RotationResourceReserveAssessment | None = None,
) -> HealerRecoveryHeavyPressure:
    """Evaluate explicit resource pressure at one possible recovery-heavy window.

    A recovery heavy is worth considering when either the current resource pool is
    at/below the caller-supplied trigger fraction or an explicitly assessed future
    healer demand has a reserve shortfall. The function does not invent either the
    trigger or the reserve floor.
    """

    now = float(time_seconds)
    maximum = int(maximum_amount)
    trigger = float(trigger_fraction)
    if not math.isfinite(now) or now < 0:
        raise ValueError("healer recovery heavy pressure time must be finite and non-negative")
    if maximum <= 0:
        raise ValueError("healer recovery heavy pressure maximum amount must be positive")
    if not math.isfinite(trigger) or not 0 <= trigger <= 1:
        raise ValueError("healer recovery heavy trigger fraction must be between 0 and 1")

    current = int(resource_amount_before(timeline, now))
    fraction = min(1.0, max(0.0, current / maximum))

    reserve_shortfall = 0
    if reserve_assessment is not None:
        requirement = reserve_assessment.requirement
        if requirement.resource is not timeline.resource:
            raise ValueError(
                "healer recovery reserve assessment resource does not match timeline: "
                f"{requirement.resource.value} != {timeline.resource.value}"
            )
        if now >= reserve_assessment.demand.start_seconds:
            raise ValueError(
                "healer recovery reserve assessment must describe a future demand window"
            )
        reserve_shortfall = int(reserve_assessment.shortfall)

    low_resource = fraction <= trigger
    recommended = low_resource or reserve_shortfall > 0

    if reserve_shortfall > 0 and low_resource:
        reason = (
            f"{timeline.resource.value} is at {fraction:.1%}, at/below the {trigger:.1%} recovery trigger, "
            f"and upcoming healer reserve is short by {reserve_shortfall}"
        )
    elif reserve_shortfall > 0:
        reason = f"upcoming healer reserve is short by {reserve_shortfall} {timeline.resource.value}"
    elif low_resource:
        reason = (
            f"{timeline.resource.value} is at {fraction:.1%}, at/below the {trigger:.1%} recovery trigger"
        )
    else:
        reason = (
            f"{timeline.resource.value} is at {fraction:.1%}, above the {trigger:.1%} recovery trigger, "
            "with no verified reserve shortfall"
        )

    return HealerRecoveryHeavyPressure(
        resource=timeline.resource,
        time_seconds=now,
        current_amount=current,
        maximum_amount=maximum,
        resource_fraction=fraction,
        trigger_fraction=trigger,
        reserve_shortfall=reserve_shortfall,
        recommended=recommended,
        reason=reason,
    )
