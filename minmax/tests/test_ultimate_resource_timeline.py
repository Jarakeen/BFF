from minmax.ultimate_resource_timeline import (
    UltimateGenerationEvent,
    UltimateResourceTimeline,
    UltimateSpendRule,
)


def test_starting_ultimate_can_make_one_cast_immediately() -> None:
    projection = UltimateResourceTimeline().project(
        starting_amount=300.0,
        events=(),
        spend_rule=UltimateSpendRule("Aggressive Horn", 250.0),
        duration_seconds=60.0,
    )

    assert projection.availability_times == (0.0,)
    assert projection.ending_amount == 50.0


def test_generation_crosses_threshold_at_event_time() -> None:
    projection = UltimateResourceTimeline().project(
        starting_amount=100.0,
        events=(
            UltimateGenerationEvent(5.0, 75.0, "explicit gain A"),
            UltimateGenerationEvent(10.0, 75.0, "explicit gain B"),
        ),
        spend_rule=UltimateSpendRule("Aggressive Horn", 250.0),
        duration_seconds=60.0,
    )

    assert projection.availability_times == (10.0,)
    assert projection.ending_amount == 0.0


def test_repeated_explicit_generation_can_fund_multiple_casts() -> None:
    projection = UltimateResourceTimeline().project(
        starting_amount=0.0,
        events=(
            UltimateGenerationEvent(5.0, 250.0, "first pool"),
            UltimateGenerationEvent(20.0, 100.0, "second pool A"),
            UltimateGenerationEvent(30.0, 150.0, "second pool B"),
        ),
        spend_rule=UltimateSpendRule("Aggressive Horn", 250.0),
        duration_seconds=60.0,
    )

    assert projection.availability_times == (5.0, 30.0)
    assert projection.ending_amount == 0.0


def test_single_large_gain_can_fund_multiple_casts_at_same_time() -> None:
    projection = UltimateResourceTimeline().project(
        starting_amount=0.0,
        events=(UltimateGenerationEvent(12.0, 500.0, "large explicit gain"),),
        spend_rule=UltimateSpendRule("Aggressive Horn", 250.0),
        duration_seconds=60.0,
    )

    assert projection.availability_times == (12.0, 12.0)
    assert projection.ending_amount == 0.0


def test_generation_event_after_duration_is_rejected() -> None:
    try:
        UltimateResourceTimeline().project(
            starting_amount=0.0,
            events=(UltimateGenerationEvent(61.0, 250.0, "too late"),),
            spend_rule=UltimateSpendRule("Aggressive Horn", 250.0),
            duration_seconds=60.0,
        )
    except ValueError as exc:
        assert "after timeline duration" in str(exc)
    else:
        raise AssertionError("Expected post-duration Ultimate gain to fail")
