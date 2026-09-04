from minmax.healer_budget_reserve_decision import propose_healer_budget_reserve_decision
from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
)
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_reserve_priority import ReserveProtectionPriority
from minmax.rotation_window_resource_budget import (
    RequiredRotationSpend,
    derive_rotation_window_resource_budget,
)


def test_budget_derived_healer_decision_repairs_entry_shortfall_with_policy_filler() -> None:
    demand = RotationDemandWindow(
        name="Ice Cage Pair",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    protected = ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar="front",
            slot=1,
            skill_name="Budding Seeds",
            tags=(
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.BURST_PREPARATION,
            ),
        ),
        ability_id=1,
    )
    discretionary = ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar="back",
            slot=1,
            skill_name="Elemental Ring",
            tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
        ),
        ability_id=2,
    )
    demand_assessment = HealerDemandPolicyAssessment(
        demand=demand,
        protected=(protected,),
        discretionary=(discretionary,),
        neutral=(),
    )

    filler = RotationAction(
        time_seconds=5.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Elemental Ring",
        bar="back",
    )
    cage_one = RotationAction(
        time_seconds=10.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Budding Seeds",
        bar="front",
    )
    cage_two = RotationAction(
        time_seconds=14.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Budding Seeds",
        bar="front",
    )
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=22.0,
        actions=(filler, cage_one, cage_two),
    )

    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=10000,
        ending_amount=0,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=5.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Elemental Ring",
                before=10000,
                attempted_change=-3000,
                applied_change=-3000,
                after=7000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=10.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Budding Seeds",
                before=7000,
                attempted_change=-5000,
                applied_change=-5000,
                after=2000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=12.0,
                kind=ResourceTimelineEventKind.RECOVERY_TICK,
                source="Magicka Recovery",
                before=2000,
                attempted_change=2000,
                applied_change=2000,
                after=4000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=14.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Budding Seeds",
                before=4000,
                attempted_change=-5000,
                applied_change=-4000,
                after=0,
                shortfall=1000,
            ),
        ),
    )

    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=20.0,
        required_spends=(
            RequiredRotationSpend(time_seconds=10.0, source="Budding Seeds"),
            RequiredRotationSpend(time_seconds=14.0, source="Budding Seeds"),
        ),
    )

    result = propose_healer_budget_reserve_decision(
        plan=plan,
        demand_assessment=demand_assessment,
        timeline=timeline,
        budget=budget,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=5.0,
                source="Elemental Ring",
                delay_order=0,
            ),
        ),
    )

    assert budget.minimum_entry_amount == 8000
    assert result.budget_reserve.requirement.minimum_amount == 8000
    assert result.budget_reserve.assessment.available_before_start == 7000
    assert result.budget_reserve.assessment.shortfall == 1000
    assert [item.candidate.source for item in result.decision.protection_plan.selected_to_withhold] == [
        "Elemental Ring"
    ]
    assert result.decision.protection_plan.reserve_repaired is True
    assert [(item.name, item.time_seconds) for item in result.decision.adjustment.adjusted_plan.actions] == [
        ("Budding Seeds", 10.0),
        ("Budding Seeds", 14.0),
    ]
    assert [(item.name, item.time_seconds) for item in plan.actions] == [
        ("Elemental Ring", 5.0),
        ("Budding Seeds", 10.0),
        ("Budding Seeds", 14.0),
    ]
