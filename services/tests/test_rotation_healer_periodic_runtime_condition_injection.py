from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from services.rotation_healer_action_healing_service import RotationHealerPeriodicHealSeed
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeEvidence,
    RotationHealerPeriodicRuntimeService,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
)


def _eligibility_service():
    return RotationRuntimeOutputEligibilityService(
        rules=(
            RotationRuntimeOutputConditionRule(
                skill_entity_id="healing_spring",
                coefficient_number=2,
                eligibility=RuntimeOutputEligibilityRule(
                    required_conditions=("target_in_heal_area",),
                    source="reviewed test healing-area condition",
                ),
            ),
        )
    )


def _seed():
    return RotationHealerPeriodicHealSeed(
        time_seconds=0.0,
        sequence=1,
        source_name="Healing Spring",
        coefficient_number=2,
        modeled_heal=100.0,
    )


def _evidence():
    return RotationHealerPeriodicRuntimeEvidence(
        source_name="Healing Spring",
        coefficient_number=2,
        duration_seconds=4.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_expiry_boundary=True,
    )


def test_injected_condition_resolver_reaches_exact_periodic_heal_ticks():
    service = RotationHealerPeriodicRuntimeService(
        output_eligibility_service=_eligibility_service(),
        condition_context_resolver=lambda event: (
            frozenset({"target_in_heal_area"})
            if event.time_seconds <= 2.0
            else frozenset()
        ),
    )

    result = service.project(
        seeds=(_seed(),),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
    )

    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [1.0, 2.0]


def test_call_specific_condition_resolver_overrides_injected_default():
    service = RotationHealerPeriodicRuntimeService(
        output_eligibility_service=_eligibility_service(),
        condition_context_resolver=lambda _event: frozenset(),
    )

    result = service.project(
        seeds=(_seed(),),
        evidence=(_evidence(),),
        horizon_seconds=10.0,
        condition_context_resolver=lambda _event: frozenset({"target_in_heal_area"}),
    )

    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [1.0, 2.0, 3.0, 4.0]
