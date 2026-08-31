from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool
from minmax.resource_timeline import ResourceCostEvent, run_resource_timeline
from minmax.restoration_events import ResourceRestorationEvent
from minmax.sustain_result import summarize_sustain


def _pool() -> StaticResourcePool:
    return StaticResourcePool(
        resource=ResourceType.MAGICKA,
        maximum=30000,
        displayed_recovery=0,
    )


def test_sustain_result_reports_success_and_ending_margin() -> None:
    timeline = run_resource_timeline(
        _pool(),
        starting_amount=10000,
        cost_events=(
            ResourceCostEvent(1.0, ResourceType.MAGICKA, 3000, "Skill A"),
            ResourceCostEvent(2.0, ResourceType.MAGICKA, 2500, "Skill B"),
        ),
        restoration_events=(
            ResourceRestorationEvent(1.5, ResourceType.MAGICKA, 1000, "Restore"),
        ),
    )

    result = summarize_sustain(timeline)

    assert result.sustains
    assert result.first_failure is None
    assert result.starting_amount == 10000
    assert result.ending_amount == 5500
    assert result.ending_margin == 5500
    assert result.minimum_amount == 5500
    assert result.total_cost_attempted == 5500
    assert result.total_cost_paid == 5500
    assert result.total_restoration_applied == 1000
    assert result.total_restoration_wasted == 0


def test_sustain_result_reports_first_failure_point_and_shortfall() -> None:
    timeline = run_resource_timeline(
        _pool(),
        starting_amount=4000,
        cost_events=(
            ResourceCostEvent(1.0, ResourceType.MAGICKA, 3000, "Skill A"),
            ResourceCostEvent(2.0, ResourceType.MAGICKA, 2500, "Skill B"),
            ResourceCostEvent(3.0, ResourceType.MAGICKA, 500, "Skill C"),
        ),
    )

    result = summarize_sustain(timeline)

    assert not result.sustains
    assert result.first_failure is not None
    assert result.first_failure.time_seconds == 2.0
    assert result.first_failure.source == "Skill B"
    assert result.first_failure.resource_before == 1000
    assert result.first_failure.attempted_cost == 2500
    assert result.first_failure.shortfall == 1500
    assert result.minimum_amount == 0
    assert result.ending_margin == 0
    assert result.total_cost_attempted == 6000
    assert result.total_cost_paid == 4000


def test_sustain_result_preserves_only_first_failure_when_later_costs_also_fail() -> None:
    timeline = run_resource_timeline(
        _pool(),
        starting_amount=1000,
        cost_events=(
            ResourceCostEvent(1.0, ResourceType.MAGICKA, 1500, "First failure"),
            ResourceCostEvent(2.0, ResourceType.MAGICKA, 500, "Second failure"),
        ),
    )

    result = summarize_sustain(timeline)

    assert result.first_failure is not None
    assert result.first_failure.time_seconds == 1.0
    assert result.first_failure.source == "First failure"
    assert result.first_failure.shortfall == 500


def test_sustain_result_counts_wasted_restoration_separately() -> None:
    timeline = run_resource_timeline(
        _pool(),
        starting_amount=29500,
        restoration_events=(
            ResourceRestorationEvent(1.0, ResourceType.MAGICKA, 1200, "Large restore"),
        ),
    )

    result = summarize_sustain(timeline)

    assert result.sustains
    assert result.ending_amount == 30000
    assert result.total_restoration_applied == 500
    assert result.total_restoration_wasted == 700
    assert result.minimum_amount == 29500
