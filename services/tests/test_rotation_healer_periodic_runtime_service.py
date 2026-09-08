from services.rotation_healer_action_healing_service import RotationHealerPeriodicHealSeed
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRefreshPolicy,
    RotationHealerPeriodicRuntimeEvidence,
    RotationHealerPeriodicRuntimeService,
)


def _seed(time=0.0, sequence=1):
    return RotationHealerPeriodicHealSeed(
        time_seconds=time,
        sequence=sequence,
        source_name="Healing Spring",
        coefficient_number=2,
        modeled_heal=100.0,
    )


def _evidence(**overrides):
    values = dict(
        source_name="Healing Spring",
        coefficient_number=2,
        duration_seconds=4.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_expiry_boundary=True,
        refresh_policy=None,
    )
    values.update(overrides)
    return RotationHealerPeriodicRuntimeEvidence(**values)


def test_single_periodic_application_expands_from_explicit_timing_evidence():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(),),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )

    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.0, 4.0]
    assert [event.modeled_heal for event in result.events] == [100.0] * 4


def test_missing_runtime_evidence_fails_closed():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(),), evidence=(), horizon_seconds=10.0
    )

    assert result.events == ()
    assert result.unresolved == (
        "Healing Spring coefficient 2: periodic healing runtime evidence unavailable",
    )


def test_repeated_applications_require_verified_refresh_behavior():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(2.5, 2)),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )

    assert result.events == ()
    assert result.unresolved == (
        "Healing Spring coefficient 2: periodic healing refresh behavior is not canonically verified",
    )


def test_verified_restart_refresh_truncates_old_future_ticks():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(2.5, 2)),
        evidence=(
            _evidence(refresh_policy=RotationHealerPeriodicRefreshPolicy.RESTART),
        ),
        horizon_seconds=10.0,
    )

    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.5, 4.5, 5.5, 6.5]
    assert result.unresolved == ()


def test_tick_at_verified_restart_boundary_is_not_double_counted():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(2.0, 2)),
        evidence=(
            _evidence(refresh_policy=RotationHealerPeriodicRefreshPolicy.RESTART),
        ),
        horizon_seconds=10.0,
    )

    assert [event.time_seconds for event in result.events] == [1.0, 3.0, 4.0, 5.0, 6.0]


def test_horizon_clips_periodic_healing_after_projection_end():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(),), evidence=(_evidence(),), horizon_seconds=2.4
    )

    assert [event.time_seconds for event in result.events] == [1.0, 2.0]


def test_expiry_boundary_can_be_explicitly_excluded():
    result = RotationHealerPeriodicRuntimeService().project(
        seeds=(_seed(),),
        evidence=(_evidence(tick_on_expiry_boundary=False),),
        horizon_seconds=10.0,
    )

    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.0]


def test_runtime_evidence_rejects_impossible_first_tick():
    try:
        _evidence(duration_seconds=2.0, first_tick_offset_seconds=3.0)
    except ValueError as exc:
        assert "first periodic heal tick cannot occur after duration" in str(exc)
    else:
        raise AssertionError("expected invalid periodic heal runtime evidence to fail")


def test_runtime_evidence_requires_source_name():
    try:
        _evidence(source_name="")
    except ValueError as exc:
        assert "requires source_name" in str(exc)
    else:
        raise AssertionError("expected missing source name to fail")
