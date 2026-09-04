from __future__ import annotations

from dataclasses import dataclass

from .resource_timeline import ResourceTimelineResult
from .rotation_demand_window import RotationDemandWindow
from .rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
    assess_rotation_resource_reserve,
)
from .rotation_window_resource_budget import RotationWindowResourceBudget


@dataclass(frozen=True)
class RotationBudgetReserveBridgeResult:
    """Reserve requirement and assessment derived from a required-action budget."""

    demand: RotationDemandWindow
    budget: RotationWindowResourceBudget
    requirement: RotationResourceReserveRequirement
    assessment: RotationResourceReserveAssessment


def create_reserve_requirement_from_window_budget(
    *,
    demand: RotationDemandWindow,
    budget: RotationWindowResourceBudget,
) -> RotationResourceReserveRequirement:
    """Turn a verified required-action window budget into a demand entry reserve.

    The budget must begin exactly when the demand begins. Its end may extend
    beyond the demand window, which is intentional for chained mechanics such as
    two staggered rescue windows where entry to the first must fund both.
    """

    if budget.start_seconds != demand.start_seconds:
        raise ValueError(
            "resource budget must start at the reserve demand entry: "
            f"{budget.start_seconds:g}s != {demand.start_seconds:g}s"
        )

    return RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=budget.resource,
        minimum_amount=budget.minimum_entry_amount,
    )


def assess_budget_derived_reserve(
    *,
    timeline: ResourceTimelineResult,
    demand: RotationDemandWindow,
    budget: RotationWindowResourceBudget,
) -> RotationBudgetReserveBridgeResult:
    """Assess actual entry resource against a derived required-action budget."""

    if timeline.resource is not budget.resource:
        raise ValueError(
            "resource budget does not match reserve timeline: "
            f"{budget.resource.value} != {timeline.resource.value}"
        )

    requirement = create_reserve_requirement_from_window_budget(
        demand=demand,
        budget=budget,
    )
    assessment = assess_rotation_resource_reserve(
        timeline=timeline,
        demand=demand,
        requirement=requirement,
    )
    return RotationBudgetReserveBridgeResult(
        demand=demand,
        budget=budget,
        requirement=requirement,
        assessment=assessment,
    )
