from services.rotation_healer_action_healing_service import RotationHealerDelayedHealSeed
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedMagnitudePolicy,
    RotationHealerDelayedMagnitudeResolution,
    RotationHealerDelayedRuntimeEvidence,
    RotationHealerDelayedRuntimeService,
)


def _seed():
    return RotationHealerDelayedHealSeed(
        time_seconds=2.0,
        sequence=4,
        source_name="Delayed Bloom",
        coefficient_number=1,
        modeled_heal=500.0,
    )


def _evidence(policy):
    return RotationHealerDelayedRuntimeEvidence(
        source_name="Delayed Bloom",
        coefficient_number=1,
        delay_seconds=4.0,
        provenance=("reviewed delayed magnitude fixture",),
        magnitude_policy=policy,
    )


def test_snapshot_policy_keeps_seed_magnitude_without_calling_runtime_resolver():
    calls = []

    def resolver(seed, time_seconds, sequence):
        calls.append((seed, time_seconds, sequence))
        return RotationHealerDelayedMagnitudeResolution(modeled_heal=999.0)

    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(),),
        evidence=(_evidence(RotationHealerDelayedMagnitudePolicy.SNAPSHOT_AT_CAST),),
        horizon_seconds=10.0,
        runtime_magnitude_resolver=resolver,
    )

    assert [(event.time_seconds, event.modeled_heal) for event in projection.events] == [
        (6.0, 500.0)
    ]
    assert calls == []
    assert projection.unresolved == ()


def test_recalculate_policy_calls_runtime_resolver_at_landing_time():
    calls = []

    def resolver(seed, time_seconds, sequence):
        calls.append((seed.source_name, time_seconds, sequence))
        return RotationHealerDelayedMagnitudeResolution(modeled_heal=725.0)

    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(),),
        evidence=(
            _evidence(RotationHealerDelayedMagnitudePolicy.RECALCULATE_AT_LANDING),
        ),
        horizon_seconds=10.0,
        runtime_magnitude_resolver=resolver,
    )

    assert [(event.time_seconds, event.modeled_heal) for event in projection.events] == [
        (6.0, 725.0)
    ]
    assert calls == [("Delayed Bloom", 6.0, 4)]
    assert projection.unresolved == ()


def test_dynamic_delayed_evaluation_requires_reviewed_magnitude_policy():
    evidence = RotationHealerDelayedRuntimeEvidence(
        source_name="Delayed Bloom",
        coefficient_number=1,
        delay_seconds=4.0,
        provenance=("coefficient-local wording: after 4 seconds",),
    )

    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(),),
        evidence=(evidence,),
        horizon_seconds=10.0,
        runtime_magnitude_resolver=lambda *args: RotationHealerDelayedMagnitudeResolution(
            modeled_heal=725.0
        ),
    )

    assert projection.events == ()
    assert projection.unresolved == (
        "Delayed Bloom coefficient 1: delayed healing magnitude snapshot/recalculation policy is not canonically verified",
    )


def test_unresolved_landing_magnitude_fails_closed():
    projection = RotationHealerDelayedRuntimeService().project(
        seeds=(_seed(),),
        evidence=(
            _evidence(RotationHealerDelayedMagnitudePolicy.RECALCULATE_AT_LANDING),
        ),
        horizon_seconds=10.0,
        runtime_magnitude_resolver=lambda *args: RotationHealerDelayedMagnitudeResolution(
            modeled_heal=None,
            unresolved=("landing state unavailable",),
        ),
    )

    assert projection.events == ()
    assert projection.unresolved == (
        "Delayed Bloom coefficient 1 at 6s: landing state unavailable",
    )
