import pytest

from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_exact_budget_reserve_decision import (
    propose_healer_exact_budget_reserve_decision,
)
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
)
from minmax.recovery_timing import ScheduledRecoveryTick, resolve_in_combat_recovery_tick
from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool
from minmax.resource_timeline import ResourceCostEvent, run_resource_timeline
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_reserve_priority import ReserveProtectionPriority
from minmax.rotation_reserve_replay import ResourceTimelineReplayInputs
from minmax.rotation_window_resource_budget import RotationWindowResourceBudget


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _assessment(demand: RotationDemandWindow) -> HealerDemandPolicyAssessment:
    discretionary = ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar="back",
            slot=1,
            skill_name="Optional Filler",
            tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
        ),
        ability_id=1,
    )
    return HealerDemandPolicyAssessment(
        demand=demand,
        protected=(),
        discretionary=(discretionary,),
        neutral=(),
    )


def _scenario(*, starting_amount: int, minimum_entry_amount: int):
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
    timeline = run_resource_timeline(
        pool,
        starting_amount=starting_amount,
        cost_events=costs,
        recovery_ticks=recovery,
    )
    replay_inputs = ResourceTimelineReplayInputs(
        pool=pool,
        starting_amount=starting_amount,
        cost_events=costs,
        recovery_ticks=recovery,
    )
    demand = _demand()
    budget = RotationWindowResourceBudget(
        resource=ResourceType.MAGICKA,
        start_seconds=demand.start_seconds,
        end_seconds=demand.end_seconds,
        required_spends=(),
        required_spend_amount=0,
        verified_gain_amount=0,
        minimum_entry_amount=minimum_entry_amount,
        ending_amount_from_minimum_entry=minimum_entry_amount,
    )
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Optional Filler",
                bar="back",
            ),
        ),
    )
    priorities = (
        ReserveProtectionPriority(
            time_seconds=5.0,
            source="Optional Filler",
            delay_order=0,
        ),
    )
    return demand, plan, timeline, replay_inputs, budget, priorities


def test_exact_healer_decision_does_not_claim_cap_wasted_recovery_repairs_reserve() -> None:
    demand, plan, timeline, replay_inputs, budget, priorities = _scenario(
        starting_amount=20000,
        minimum_entry_amount=16000,
    )

    result = propose_healer_exact_budget_reserve_decision(
        plan=plan,
        demand_assessment=_assessment(demand),
        timeline=timeline,
        budget=budget,
        priorities=priorities,
        replay_inputs=replay_inputs,
    )

    # Arithmetic analysis still sees the nominal 2500 spend and would predict
    # 17500. Exact replay correctly sees the recovery tick become wasted at cap,
    # so mechanic entry remains 15000 and the reserve is still not repaired.
    assert result.healer_bridge.reserve_analysis.projected_available_if_all_withheld == 17500
    assert result.exact_protection.replayed_assessment.available_before_start == 15000
    assert result.decision.protection_plan.projected_available_after_selected == 15000
    assert result.decision.protection_plan.reserve_repaired is False
    assert [item.candidate_source for item in result.decision.adjustment.withheld_actions] == [
        "Optional Filler"
    ]


def test_exact_healer_decision_withholds_cast_when_replay_proves_entry_gain_survives() -> None:
    demand, plan, timeline, replay_inputs, budget, priorities = _scenario(
        starting_amount=15000,
        minimum_entry_amount=12000,
    )

    result = propose_healer_exact_budget_reserve_decision(
        plan=plan,
        demand_assessment=_assessment(demand),
        timeline=timeline,
        budget=budget,
        priorities=priorities,
        replay_inputs=replay_inputs,
    )

    assert result.budget_reserve.assessment.available_before_start == 10000
    assert result.exact_protection.replayed_assessment.available_before_start == 12500
    assert result.decision.protection_plan.reserve_repaired is True
    assert [item.candidate_source for item in result.decision.adjustment.withheld_actions] == [
        "Optional Filler"
    ]
    assert result.decision.adjustment.adjusted_plan.actions == ()


def test_exact_healer_decision_rejects_replay_inputs_from_a_different_baseline() -> None:
    demand, plan, timeline, replay_inputs, budget, priorities = _scenario(
        starting_amount=15000,
        minimum_entry_amount=12000,
    )
    mismatched = ResourceTimelineReplayInputs(
        pool=replay_inputs.pool,
        starting_amount=14000,
        cost_events=replay_inputs.cost_events,
        recovery_ticks=replay_inputs.recovery_ticks,
        restoration_events=replay_inputs.restoration_events,
    )

    with pytest.raises(ValueError, match="do not reproduce analyzed demand-entry resource"):
        propose_healer_exact_budget_reserve_decision(
            plan=plan,
            demand_assessment=_assessment(demand),
            timeline=timeline,
            budget=budget,
            priorities=priorities,
            replay_inputs=mismatched,
        )
