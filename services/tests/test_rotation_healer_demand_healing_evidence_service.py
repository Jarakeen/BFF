from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerDelayedHealSeed,
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeProjection,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidenceService,
)


def _demand(kind=RotationDemandKind.HEALING):
    return RotationDemandWindow(
        name="Ice Cage",
        start_seconds=10.0,
        end_seconds=14.0,
        kind=kind,
        pattern=RotationDemandPattern.BURST,
    )


def _direct(time_seconds, amount=1000.0, name="Burst Heal"):
    return RotationHealerResolvedHealEvent(
        time_seconds=time_seconds,
        sequence=1,
        source_name=name,
        coefficient_number=1,
        modeled_heal=amount,
    )


def _periodic(time_seconds, amount=250.0, name="HoT"):
    return RotationHealerPeriodicHealSeed(
        time_seconds=time_seconds,
        sequence=1,
        source_name=name,
        coefficient_number=2,
        modeled_heal=amount,
    )


def _delayed(time_seconds, amount=3500.0, name="Budding Seeds"):
    return RotationHealerDelayedHealSeed(
        time_seconds=time_seconds,
        sequence=1,
        source_name=name,
        coefficient_number=1,
        modeled_heal=amount,
    )


def test_collects_direct_heals_inside_explicit_demand_window():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(
                _direct(9.5, 500.0),
                _direct(10.0, 1000.0),
                _direct(12.0, 1500.0),
                _direct(14.0, 2000.0),
                _direct(14.5, 3000.0),
            ),
            periodic_seeds=(),
            unresolved=(),
        ),
    )

    assert [event.time_seconds for event in result.direct_events] == [10.0, 12.0, 14.0]
    assert result.modeled_direct_healing == 4500.0
    assert result.has_timed_direct_heal
    assert result.modeled_delayed_healing == 0.0
    assert not result.has_timed_delayed_heal
    assert result.unresolved == ()


def test_no_heal_in_window_is_observation_not_invented_failure_threshold():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(_direct(5.0),),
            periodic_seeds=(),
            unresolved=(),
        ),
    )

    assert result.direct_events == ()
    assert result.modeled_direct_healing == 0.0
    assert not result.has_timed_direct_heal
    assert result.unresolved == ()


def test_periodic_seed_before_window_blocks_complete_coverage_claim():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(_direct(12.0),),
            periodic_seeds=(_periodic(8.0, name="Illustrious Healing"),),
            unresolved=(),
        ),
    )

    assert result.modeled_direct_healing == 1000.0
    assert result.unresolved == (
        "Ice Cage: periodic healing runtime is unresolved for demand coverage (Illustrious Healing)",
    )


def test_periodic_seed_after_demand_does_not_block_that_earlier_window():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(_direct(12.0),),
            periodic_seeds=(_periodic(15.0),),
            unresolved=(),
        ),
    )

    assert result.unresolved == ()


def test_delayed_seed_before_window_requires_runtime_projection():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(),
            delayed_seeds=(_delayed(5.0),),
            unresolved=(),
        ),
    )

    assert result.delayed_events == ()
    assert result.modeled_delayed_healing == 0.0
    assert result.unresolved == (
        "Ice Cage: delayed healing runtime is unresolved for demand coverage (Budding Seeds)",
    )


def test_timed_delayed_bloom_inside_window_counts_as_delayed_healing_evidence():
    delayed_projection = RotationHealerDelayedRuntimeProjection(
        events=(
            _direct(9.0, 3500.0, name="Budding Seeds"),
            _direct(11.0, 3500.0, name="Budding Seeds"),
            _direct(15.0, 3500.0, name="Budding Seeds"),
        ),
        unresolved=(),
    )
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(_direct(12.0, 1000.0),),
            periodic_seeds=(),
            delayed_seeds=(_delayed(5.0),),
            unresolved=(),
        ),
        delayed_projection=delayed_projection,
    )

    assert [event.time_seconds for event in result.delayed_events] == [11.0]
    assert result.modeled_delayed_healing == 3500.0
    assert result.has_timed_delayed_heal
    assert result.modeled_total_healing == 4500.0
    assert result.unresolved == ()


def test_projection_unresolved_is_preserved():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(),
            unresolved=("heal component identity unresolved",),
        ),
    )

    assert result.unresolved == ("heal component identity unresolved",)


def test_non_healing_demand_is_rejected():
    try:
        RotationHealerDemandHealingEvidenceService().assess(
            demand=_demand(RotationDemandKind.DAMAGE),
            projection=RotationHealerActionHealingProjection(
                direct_events=(),
                periodic_seeds=(),
                unresolved=(),
            ),
        )
    except ValueError as exc:
        assert "requires a healing demand window" in str(exc)
    else:
        raise AssertionError("expected non-healing demand to be rejected")
