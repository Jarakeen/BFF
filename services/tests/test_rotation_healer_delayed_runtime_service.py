from services.rotation_healer_action_healing_service import RotationHealerDelayedHealSeed
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
    RotationHealerDelayedRuntimeService,
    extract_delayed_heal_runtime_evidence,
)


def _seed(*, time_seconds=4.0, sequence=2):
    return RotationHealerDelayedHealSeed(
        time_seconds=time_seconds,
        sequence=sequence,
        source_name="Budding Seeds",
        coefficient_number=1,
        modeled_heal=3500.0,
    )


def _evidence():
    return RotationHealerDelayedRuntimeEvidence(
        source_name="Budding Seeds",
        coefficient_number=1,
        delay_seconds=6.0,
        provenance=("coefficient-local wording: after 6 seconds",),
    )


def test_extracts_explicit_after_seconds_delay():
    evidence = extract_delayed_heal_runtime_evidence(
        source_name="Budding Seeds",
        coefficient_number=1,
        component_fragment=(
            "Summon a field of flowers which blooms after 6 seconds, "
            "healing you and allies in the area for $1 Health."
        ),
    )

    assert evidence is not None
    assert evidence.delay_seconds == 6.0
    assert evidence.provenance == ("coefficient-local wording: after 6 seconds",)


def test_does_not_treat_over_duration_as_delayed_event_timing():
    evidence = extract_delayed_heal_runtime_evidence(
        source_name="Imaginary Heal",
        coefficient_number=1,
        component_fragment="Heal allies for $1 Health over 6 seconds.",
    )

    assert evidence is None


def test_schedules_delayed_heal_at_cast_plus_verified_delay():
    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(time_seconds=4.0),),
        evidence=(_evidence(),),
        horizon_seconds=20.0,
    )

    assert projection.unresolved == ()
    assert len(projection.events) == 1
    event = projection.events[0]
    assert event.time_seconds == 10.0
    assert event.sequence == 2
    assert event.source_name == "Budding Seeds"
    assert event.coefficient_number == 1
    assert event.modeled_heal == 3500.0


def test_missing_delayed_runtime_evidence_fails_closed():
    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(),),
        evidence=(),
        horizon_seconds=20.0,
    )

    assert projection.events == ()
    assert projection.unresolved == (
        "Budding Seeds coefficient 1: delayed healing runtime evidence unavailable",
    )


def test_delayed_event_beyond_horizon_is_clipped_without_fabricating_partial_heal():
    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(time_seconds=8.0),),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )

    assert projection.events == ()
    assert projection.unresolved == ()


def test_multiple_delayed_activations_schedule_independently_when_no_transform_rule_is_applied():
    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(time_seconds=1.0, sequence=0), _seed(time_seconds=3.0, sequence=1)),
        evidence=(_evidence(),),
        horizon_seconds=20.0,
    )

    assert [event.time_seconds for event in projection.events] == [7.0, 9.0]
    assert projection.unresolved == ()
