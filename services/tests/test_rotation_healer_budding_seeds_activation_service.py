from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerDelayedHealSeed,
    RotationHealerPeriodicHealSeed,
)
from services.rotation_healer_budding_seeds_activation_service import (
    RotationHealerBuddingSeedsActivationService,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)


def _plan(*times):
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(
            RotationAction(
                time_seconds=float(time_seconds),
                sequence=index + 1,
                kind=RotationActionKind.SKILL,
                name="Budding Seeds",
                bar="front",
            )
            for index, time_seconds in enumerate(times)
        ),
    )


def _healing(*times):
    delayed = tuple(
        RotationHealerDelayedHealSeed(
            time_seconds=float(time_seconds),
            sequence=index + 1,
            source_name="Budding Seeds",
            coefficient_number=1,
            modeled_heal=3000.0,
        )
        for index, time_seconds in enumerate(times)
    )
    periodic = tuple(
        RotationHealerPeriodicHealSeed(
            time_seconds=float(time_seconds),
            sequence=index + 1,
            source_name="Budding Seeds",
            coefficient_number=2,
            modeled_heal=400.0,
        )
        for index, time_seconds in enumerate(times)
    )
    return RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=periodic,
        unresolved=(),
        delayed_seeds=delayed,
    )


def _evidence():
    return RotationHealerDelayedRuntimeEvidence(
        source_name="Budding Seeds",
        coefficient_number=1,
        delay_seconds=6.0,
        provenance=("tooltip: blooms after 6 seconds",),
    )


def test_second_activation_before_natural_bloom_emits_immediate_first_field_bloom():
    result = RotationHealerBuddingSeedsActivationService().project(
        plan=_plan(10.0, 13.0),
        healing=_healing(10.0, 13.0),
        delayed_evidence=_evidence(),
    )

    assert len(result.special_events) == 1
    event = result.special_events[0]
    assert event.time_seconds == 13.0
    assert event.sequence == 2
    assert event.coefficient_number == 1
    assert event.modeled_heal == 3000.0


def test_second_activation_suppresses_generic_new_field_seeds_for_transformed_pair():
    result = RotationHealerBuddingSeedsActivationService().project(
        plan=_plan(10.0, 13.0),
        healing=_healing(10.0, 13.0),
        delayed_evidence=_evidence(),
    )

    assert result.delayed_seeds == ()
    assert result.periodic_seeds == ()
    assert result.unresolved == (
        "Budding Seeds coefficient 2: periodic field termination boundary at second activation is not independently verified",
    )


def test_activation_at_natural_bloom_boundary_is_not_reclassified_as_early_second_activation():
    result = RotationHealerBuddingSeedsActivationService().project(
        plan=_plan(10.0, 16.0),
        healing=_healing(10.0, 16.0),
        delayed_evidence=_evidence(),
    )

    assert result.special_events == ()
    assert len(result.delayed_seeds) == 2
    assert len(result.periodic_seeds) == 2
    assert result.unresolved == ()


def test_later_recast_after_natural_bloom_remains_an_ordinary_new_field():
    result = RotationHealerBuddingSeedsActivationService().project(
        plan=_plan(2.0, 9.0),
        healing=_healing(2.0, 9.0),
        delayed_evidence=_evidence(),
    )

    assert result.special_events == ()
    assert [seed.time_seconds for seed in result.delayed_seeds] == [2.0, 9.0]
    assert [seed.time_seconds for seed in result.periodic_seeds] == [2.0, 9.0]


def test_unrelated_healer_seeds_are_preserved():
    healing = _healing(10.0, 13.0)
    healing = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=healing.periodic_seeds + (
            RotationHealerPeriodicHealSeed(
                time_seconds=11.0,
                sequence=90,
                source_name="Illustrious Healing",
                coefficient_number=1,
                modeled_heal=500.0,
            ),
        ),
        unresolved=(),
        delayed_seeds=healing.delayed_seeds,
    )

    result = RotationHealerBuddingSeedsActivationService().project(
        plan=_plan(10.0, 13.0),
        healing=healing,
        delayed_evidence=_evidence(),
    )

    assert len(result.periodic_seeds) == 1
    assert result.periodic_seeds[0].source_name == "Illustrious Healing"


def test_wrong_delayed_evidence_identity_is_rejected():
    evidence = RotationHealerDelayedRuntimeEvidence(
        source_name="Other Heal",
        coefficient_number=1,
        delay_seconds=6.0,
    )

    try:
        RotationHealerBuddingSeedsActivationService().project(
            plan=_plan(10.0, 13.0),
            healing=_healing(10.0, 13.0),
            delayed_evidence=evidence,
        )
    except ValueError as exc:
        assert "requires Budding Seeds delayed evidence" in str(exc)
    else:
        raise AssertionError("expected mismatched evidence to be rejected")
