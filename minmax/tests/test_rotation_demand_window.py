from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
    create_staggered_burst_demands,
)


def test_staggered_burst_demands_keep_independent_rescue_deadlines() -> None:
    first, second = create_staggered_burst_demands(
        name="Ice Cage",
        first_start_seconds=0.0,
        second_start_seconds=9.0,
        deadline_seconds=7.0,
    )

    assert (first.start_seconds, first.end_seconds, first.duration_seconds) == (0.0, 7.0, 7.0)
    assert (second.start_seconds, second.end_seconds, second.duration_seconds) == (9.0, 16.0, 7.0)
    assert first.pattern is RotationDemandPattern.BURST
    assert second.kind is RotationDemandKind.HEALING


def test_sustained_demand_can_model_long_healing_pressure_without_inventing_output_threshold() -> None:
    demand = RotationDemandWindow(
        name="Bahsei tank bleed",
        start_seconds=0,
        end_seconds=180,
        kind="healing",
        pattern="sustained",
        target_count=2,
    )

    assert demand.duration_seconds == 180.0
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.pattern is RotationDemandPattern.SUSTAINED
    assert demand.target_count == 2
    assert not hasattr(demand, "required_hps")


def test_rotation_demand_window_rejects_invalid_boundaries() -> None:
    invalid = (
        lambda: RotationDemandWindow(
            name="",
            start_seconds=0,
            end_seconds=1,
            kind="damage",
            pattern="burst",
        ),
        lambda: RotationDemandWindow(
            name="bad",
            start_seconds=2,
            end_seconds=1,
            kind="damage",
            pattern="burst",
        ),
        lambda: RotationDemandWindow(
            name="bad",
            start_seconds=0,
            end_seconds=1,
            kind="damage",
            pattern="burst",
            target_count=0,
        ),
    )

    for create in invalid:
        try:
            create()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid rotation demand to be rejected")
