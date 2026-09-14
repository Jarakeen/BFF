from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from services.rotation_healer_action_healing_service import (
    RotationHealerChannelHealSeed,
    RotationHealerDelayedHealSeed,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelRuntimeEvidence,
    RotationHealerChannelRuntimeService,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
    RotationHealerDelayedRuntimeService,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
)


def _eligibility_service(skill_entity_id: str, coefficient_number: int, condition: str):
    return RotationRuntimeOutputEligibilityService(
        rules=(
            RotationRuntimeOutputConditionRule(
                skill_entity_id=skill_entity_id,
                coefficient_number=coefficient_number,
                eligibility=RuntimeOutputEligibilityRule(
                    required_conditions=(condition,),
                    source="reviewed healer runtime-condition test evidence",
                ),
            ),
        )
    )


def test_delayed_heal_checks_condition_at_landing_not_cast_time():
    service = RotationHealerDelayedRuntimeService(
        output_eligibility_service=_eligibility_service(
            "budding_seeds", 2, "target_in_bloom_area"
        )
    )
    seed = RotationHealerDelayedHealSeed(
        time_seconds=1.0,
        sequence=3,
        source_name="Budding Seeds",
        coefficient_number=2,
        modeled_heal=500.0,
    )
    evidence = RotationHealerDelayedRuntimeEvidence(
        source_name="Budding Seeds",
        coefficient_number=2,
        delay_seconds=6.0,
    )

    unresolved = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=10.0,
    )
    assert unresolved.events == ()
    assert len(unresolved.unresolved) == 1
    assert "at 7s" in unresolved.unresolved[0]
    assert "authoritative ConditionContext" in unresolved.unresolved[0]

    ineligible = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=10.0,
        condition_context_resolver=lambda _event: frozenset(),
    )
    assert ineligible.events == ()
    assert ineligible.unresolved == ()

    eligible = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=10.0,
        condition_context_resolver=lambda _event: frozenset({"target_in_bloom_area"}),
    )
    assert eligible.unresolved == ()
    assert [event.time_seconds for event in eligible.events] == [7.0]


def test_delayed_service_level_condition_resolver_can_be_overridden_per_call():
    service = RotationHealerDelayedRuntimeService(
        output_eligibility_service=_eligibility_service(
            "budding_seeds", 2, "target_in_bloom_area"
        ),
        condition_context_resolver=lambda _event: frozenset(),
    )
    seed = RotationHealerDelayedHealSeed(
        time_seconds=0.0,
        sequence=1,
        source_name="Budding Seeds",
        coefficient_number=2,
        modeled_heal=500.0,
    )
    evidence = RotationHealerDelayedRuntimeEvidence(
        source_name="Budding Seeds",
        coefficient_number=2,
        delay_seconds=2.0,
    )

    default_result = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=5.0,
    )
    assert default_result.events == ()
    assert default_result.unresolved == ()

    override = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=5.0,
        condition_context_resolver=lambda _event: frozenset({"target_in_bloom_area"}),
    )
    assert [event.time_seconds for event in override.events] == [2.0]


def test_channel_heal_checks_condition_independently_for_each_tick():
    service = RotationHealerChannelRuntimeService(
        output_eligibility_service=_eligibility_service(
            "radiant_regeneration_channel", 1, "target_in_channel_range"
        )
    )
    seed = RotationHealerChannelHealSeed(
        time_seconds=0.0,
        sequence=2,
        source_name="Radiant Regeneration Channel",
        coefficient_number=1,
        modeled_heal=250.0,
    )
    evidence = RotationHealerChannelRuntimeEvidence(
        source_name="Radiant Regeneration Channel",
        coefficient_number=1,
        channel_duration_seconds=4.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_channel_end_boundary=True,
    )

    unresolved = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=6.0,
    )
    assert unresolved.events == ()
    assert len(unresolved.unresolved) == 4
    assert "at 1s" in unresolved.unresolved[0]
    assert "at 4s" in unresolved.unresolved[-1]

    mixed = service.project(
        seeds=(seed,),
        evidence=(evidence,),
        horizon_seconds=6.0,
        condition_context_resolver=lambda event: (
            frozenset({"target_in_channel_range"})
            if event.time_seconds in {1.0, 3.0}
            else frozenset()
        ),
    )
    assert mixed.unresolved == ()
    assert [event.time_seconds for event in mixed.events] == [1.0, 3.0]


def test_unreviewed_delayed_and_channel_output_remain_backward_compatible():
    delayed = RotationHealerDelayedRuntimeService().project(
        seeds=(
            RotationHealerDelayedHealSeed(
                time_seconds=0.0,
                sequence=1,
                source_name="Ordinary Delayed Heal",
                coefficient_number=1,
                modeled_heal=100.0,
            ),
        ),
        evidence=(
            RotationHealerDelayedRuntimeEvidence(
                source_name="Ordinary Delayed Heal",
                coefficient_number=1,
                delay_seconds=2.0,
            ),
        ),
        horizon_seconds=5.0,
    )
    assert delayed.unresolved == ()
    assert [event.time_seconds for event in delayed.events] == [2.0]

    channel = RotationHealerChannelRuntimeService().project(
        seeds=(
            RotationHealerChannelHealSeed(
                time_seconds=0.0,
                sequence=1,
                source_name="Ordinary Channel Heal",
                coefficient_number=1,
                modeled_heal=100.0,
            ),
        ),
        evidence=(
            RotationHealerChannelRuntimeEvidence(
                source_name="Ordinary Channel Heal",
                coefficient_number=1,
                channel_duration_seconds=2.0,
                tick_interval_seconds=1.0,
                first_tick_offset_seconds=1.0,
                tick_on_channel_end_boundary=True,
            ),
        ),
        horizon_seconds=5.0,
    )
    assert channel.unresolved == ()
    assert [event.time_seconds for event in channel.events] == [1.0, 2.0]
