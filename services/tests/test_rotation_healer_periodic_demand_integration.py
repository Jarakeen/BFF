from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidenceService,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeProjection,
)


def _demand():
    return RotationDemandWindow(
        name="Ice Cage",
        start_seconds=10.0,
        end_seconds=14.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _direct(time_seconds=12.0, amount=1000.0):
    return RotationHealerResolvedHealEvent(
        time_seconds=time_seconds,
        sequence=1,
        source_name="Burst Heal",
        coefficient_number=1,
        modeled_heal=amount,
    )


def _seed(time_seconds=8.0):
    return RotationHealerPeriodicHealSeed(
        time_seconds=time_seconds,
        sequence=1,
        source_name="Illustrious Healing",
        coefficient_number=2,
        modeled_heal=250.0,
    )


def _tick(time_seconds, amount=250.0):
    return RotationHealerResolvedHealEvent(
        time_seconds=time_seconds,
        sequence=int(time_seconds * 10),
        source_name="Illustrious Healing",
        coefficient_number=2,
        modeled_heal=amount,
    )


def test_scheduled_periodic_ticks_are_counted_inside_demand_window():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(_direct(),),
            periodic_seeds=(_seed(),),
            unresolved=(),
        ),
        periodic_projection=RotationHealerPeriodicRuntimeProjection(
            events=(_tick(9.0), _tick(10.0), _tick(12.0), _tick(14.0), _tick(15.0)),
            unresolved=(),
        ),
    )

    assert [event.time_seconds for event in result.periodic_events] == [10.0, 12.0, 14.0]
    assert result.modeled_direct_healing == 1000.0
    assert result.modeled_periodic_healing == 750.0
    assert result.modeled_total_healing == 1750.0
    assert result.has_timed_periodic_heal
    assert result.unresolved == ()


def test_runtime_unresolved_is_preserved_even_with_some_timed_ticks():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(_seed(),),
            unresolved=(),
        ),
        periodic_projection=RotationHealerPeriodicRuntimeProjection(
            events=(_tick(12.0),),
            unresolved=("Illustrious Healing refresh behavior unresolved",),
        ),
    )

    assert result.modeled_periodic_healing == 250.0
    assert result.unresolved == ("Illustrious Healing refresh behavior unresolved",)


def test_missing_periodic_projection_retains_existing_fail_closed_diagnostic():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(_seed(),),
            unresolved=(),
        ),
    )

    assert result.periodic_events == ()
    assert result.modeled_periodic_healing == 0.0
    assert result.unresolved == (
        "Ice Cage: periodic healing runtime is unresolved for demand coverage (Illustrious Healing)",
    )


def test_periodic_runtime_can_contribute_without_a_direct_heal():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(_seed(),),
            unresolved=(),
        ),
        periodic_projection=RotationHealerPeriodicRuntimeProjection(
            events=(_tick(11.0), _tick(13.0)),
            unresolved=(),
        ),
    )

    assert not result.has_timed_direct_heal
    assert result.has_timed_periodic_heal
    assert result.modeled_total_healing == 500.0
