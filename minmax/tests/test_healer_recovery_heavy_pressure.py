import pytest

from minmax.healer_recovery_heavy_pressure import evaluate_healer_recovery_heavy_pressure
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)


def _timeline(starting: int) -> ResourceTimelineResult:
    return ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=starting,
        ending_amount=starting,
        events=(),
    )


def _reserve(*, available: int, minimum: int = 6000) -> RotationResourceReserveAssessment:
    demand = RotationDemandWindow(
        name="Incoming burst heal",
        start_seconds=10.0,
        end_seconds=12.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    requirement = RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=ResourceType.MAGICKA,
        minimum_amount=minimum,
    )
    return RotationResourceReserveAssessment(
        demand=demand,
        requirement=requirement,
        available_before_start=available,
    )


def test_low_resource_creates_recovery_heavy_pressure() -> None:
    result = evaluate_healer_recovery_heavy_pressure(
        timeline=_timeline(2500),
        time_seconds=4.0,
        maximum_amount=10000,
        trigger_fraction=0.30,
    )

    assert result.recommended is True
    assert result.resource_fraction == 0.25
    assert result.reserve_shortfall == 0
    assert "at/below" in result.reason


def test_healthy_resource_without_reserve_shortfall_does_not_create_pressure() -> None:
    result = evaluate_healer_recovery_heavy_pressure(
        timeline=_timeline(7000),
        time_seconds=4.0,
        maximum_amount=10000,
        trigger_fraction=0.30,
    )

    assert result.recommended is False
    assert result.resource_fraction == 0.70
    assert "no verified reserve shortfall" in result.reason


def test_future_healer_reserve_shortfall_creates_pressure_even_above_fraction_trigger() -> None:
    result = evaluate_healer_recovery_heavy_pressure(
        timeline=_timeline(7000),
        time_seconds=4.0,
        maximum_amount=10000,
        trigger_fraction=0.30,
        reserve_assessment=_reserve(available=4500, minimum=6000),
    )

    assert result.recommended is True
    assert result.resource_fraction == 0.70
    assert result.reserve_shortfall == 1500
    assert "short by 1500" in result.reason


def test_reserve_assessment_must_describe_future_matching_resource() -> None:
    reserve = _reserve(available=4500)

    with pytest.raises(ValueError, match="future demand"):
        evaluate_healer_recovery_heavy_pressure(
            timeline=_timeline(7000),
            time_seconds=10.0,
            maximum_amount=10000,
            trigger_fraction=0.30,
            reserve_assessment=reserve,
        )
