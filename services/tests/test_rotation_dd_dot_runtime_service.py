from minmax.dd_damage import DDDamageEvent
from services.rotation_dd_action_damage_event_service import RotationDDDotComponentSeed
from services.rotation_dd_dot_runtime_service import (
    RotationDDDotRuntimeEvidence,
    RotationDDDotRuntimeService,
)


def _seed(time=0.0, sequence=1):
    return RotationDDDotComponentSeed(
        cast_time_seconds=time,
        sequence=sequence,
        source_name="Burning Dot",
        coefficient_number=2,
        event=DDDamageEvent(
            base_value=100.0,
            damage_type="flame",
            can_crit=True,
            is_dot=True,
        ),
    )


def _evidence(**overrides):
    values = dict(
        source_name="Burning Dot",
        coefficient_number=2,
        duration_seconds=4.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_expiry_boundary=True,
    )
    values.update(overrides)
    return RotationDDDotRuntimeEvidence(**values)


def test_expands_only_from_explicit_runtime_evidence():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(),), evidence=(_evidence(),), horizon_seconds=10.0
    )
    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.0, 4.0]
    assert all(event.event.is_dot for event in result.events)


def test_missing_runtime_evidence_fails_closed():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(),), evidence=(), horizon_seconds=10.0
    )
    assert result.events == ()
    assert result.unresolved == (
        "Burning Dot coefficient 2: DoT runtime evidence unavailable",
    )


def test_recast_restart_truncates_old_future_ticks():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(2.5, 2)),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )
    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.5, 4.5, 5.5, 6.5]


def test_tick_exactly_at_recast_boundary_is_not_double_counted():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(2.0, 2)),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )
    assert [event.time_seconds for event in result.events] == [1.0, 3.0, 4.0, 5.0, 6.0]


def test_horizon_clips_ticks_after_target_death_or_projection_end():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(),), evidence=(_evidence(),), horizon_seconds=2.4
    )
    assert [event.time_seconds for event in result.events] == [1.0, 2.0]


def test_expiry_boundary_can_be_explicitly_excluded():
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(),),
        evidence=(_evidence(tick_on_expiry_boundary=False),),
        horizon_seconds=10.0,
    )
    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.0]


def test_runtime_evidence_rejects_impossible_first_tick():
    try:
        _evidence(duration_seconds=2.0, first_tick_offset_seconds=3.0)
    except ValueError as exc:
        assert "first DoT tick cannot occur after duration" in str(exc)
    else:
        raise AssertionError("expected invalid runtime evidence to fail")
