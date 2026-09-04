import pytest

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_budget_reserve_bridge import (
    assess_budget_derived_reserve,
    create_reserve_requirement_from_window_budget,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_window_resource_budget import RotationWindowResourceBudget


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _budget(*, start: float = 10.0, minimum_entry: int = 12000) -> RotationWindowResourceBudget:
    return RotationWindowResourceBudget(
        resource=ResourceType.MAGICKA,
        start_seconds=start,
        end_seconds=26.0,
        required_spends=(),
        required_spend_amount=15000,
        verified_gain_amount=5000,
        minimum_entry_amount=minimum_entry,
        ending_amount_from_minimum_entry=2000,
    )


def test_paired_window_budget_becomes_first_demand_entry_requirement() -> None:
    demand = _demand()
    requirement = create_reserve_requirement_from_window_budget(
        demand=demand,
        budget=_budget(),
    )

    assert requirement.demand_name == "Ice Cage 1"
    assert requirement.resource is ResourceType.MAGICKA
    assert requirement.minimum_amount == 12000


def test_budget_derived_assessment_uses_actual_resource_before_demand_start() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=11000,
        ending_amount=11000,
        events=(),
    )

    result = assess_budget_derived_reserve(
        timeline=timeline,
        demand=_demand(),
        budget=_budget(minimum_entry=12000),
    )

    assert result.requirement.minimum_amount == 12000
    assert result.assessment.available_before_start == 11000
    assert result.assessment.shortfall == 1000
    assert result.assessment.satisfied is False


def test_budget_must_begin_at_demand_entry() -> None:
    with pytest.raises(ValueError, match="must start at the reserve demand entry"):
        create_reserve_requirement_from_window_budget(
            demand=_demand(),
            budget=_budget(start=9.0),
        )


def test_budget_resource_must_match_assessment_timeline() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.STAMINA,
        starting_amount=12000,
        ending_amount=12000,
        events=(),
    )

    with pytest.raises(ValueError, match="does not match reserve timeline"):
        assess_budget_derived_reserve(
            timeline=timeline,
            demand=_demand(),
            budget=_budget(),
        )
