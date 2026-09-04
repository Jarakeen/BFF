from minmax.recovery_timing import ScheduledRecoveryTick, resolve_in_combat_recovery_tick
from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool
from minmax.resource_timeline import (
    ResourceCostEvent,
    ResourceTimelineEventKind,
    run_resource_timeline,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_reserve_priority import ReserveProtectionPriority
from minmax.rotation_reserve_protection import (
    DiscretionaryRotationSpend,
    analyze_rotation_reserve_protection,
)
from minmax.rotation_reserve_replay import (
    ResourceTimelineReplayInputs,
    plan_exact_rotation_reserve_protection,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveRequirement,
    assess_rotation_resource_reserve,
)


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _inputs(*, starting_amount: int) -> tuple[ResourceTimelineReplayInputs, object]:
    pool = StaticResourcePool(
        resource=ResourceType.MAGICKA,
        maximum=20000,
        displayed_recovery=2500,
    )
    costs = (
        ResourceCostEvent(
            time_seconds=5.0,
            resource=ResourceType.MAGICKA,
            amount=2500,
            source="Optional Filler",
        ),
        ResourceCostEvent(
            time_seconds=8.0,
            resource=ResourceType.MAGICKA,
            amount=5000,
            source="Required Setup",
        ),
    )
    recovery = (
        ScheduledRecoveryTick(
            time_seconds=6.0,
            tick=resolve_in_combat_recovery_tick(pool),
        ),
    )
    inputs = ResourceTimelineReplayInputs(
        pool=pool,
        starting_amount=starting_amount,
        cost_events=costs,
        recovery_ticks=recovery,
    )
    timeline = run_resource_timeline(
        pool,
        starting_amount=starting_amount,
        cost_events=costs,
        recovery_ticks=recovery,
    )
    return inputs, timeline


def _analysis(*, starting_amount: int, required: int):
    inputs, timeline = _inputs(starting_amount=starting_amount)
    demand = _demand()
    requirement = RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=ResourceType.MAGICKA,
        minimum_amount=required,
    )
    assessment = assess_rotation_resource_reserve(
        timeline=timeline,
        demand=demand,
        requirement=requirement,
    )
    analysis = analyze_rotation_reserve_protection(
        timeline=timeline,
        reserve_assessment=assessment,
        discretionary_spends=(
            DiscretionaryRotationSpend(5.0, "Optional Filler"),
        ),
    )
    return inputs, timeline, analysis


def test_exact_replay_does_not_overcredit_withheld_spend_when_recovery_hits_cap() -> None:
    inputs, _timeline, analysis = _analysis(starting_amount=20000, required=16000)

    # The legacy arithmetic view overestimates this case: it adds the 2500 cost
    # back to the 15000 entry amount and predicts 17500. Exact replay shows that
    # the 6s recovery tick simply becomes wasted while capped, leaving 15000.
    assert analysis.reserve_assessment.available_before_start == 15000
    assert analysis.projected_available_if_all_withheld == 17500
    assert analysis.can_repair_shortfall is True

    exact = plan_exact_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=5.0,
                source="Optional Filler",
                delay_order=0,
            ),
        ),
        replay_inputs=inputs,
    )

    assert [item.candidate.source for item in exact.protection_plan.selected_to_withhold] == [
        "Optional Filler"
    ]
    assert exact.replayed_assessment.available_before_start == 15000
    assert exact.protection_plan.projected_available_after_selected == 15000
    assert exact.protection_plan.projected_shortfall_after_selected == 1000
    assert exact.protection_plan.reserve_repaired is False

    recovery_event = next(
        event
        for event in exact.replayed_timeline.events
        if event.kind is ResourceTimelineEventKind.RECOVERY_TICK
    )
    assert recovery_event.wasted_restore == 2500


def test_exact_replay_credits_withheld_spend_when_recovery_still_fits_below_cap() -> None:
    inputs, _timeline, analysis = _analysis(starting_amount=15000, required=12000)

    assert analysis.reserve_assessment.available_before_start == 10000

    exact = plan_exact_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=5.0,
                source="Optional Filler",
                delay_order=0,
            ),
        ),
        replay_inputs=inputs,
    )

    assert exact.replayed_assessment.available_before_start == 12500
    assert exact.protection_plan.projected_available_after_selected == 12500
    assert exact.protection_plan.reserve_repaired is True
