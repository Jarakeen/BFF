import pytest

from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_exact_sequential_reserve import (
    HealerExactSequentialReserveStep,
    propose_exact_sequential_healer_reserve_decisions,
)
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
)
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
from minmax.rotation_window_resource_budget import (
    RequiredRotationSpend,
    derive_rotation_window_resource_budget,
)


_COST_BY_SKILL = {
    "Elemental Ring": 3000,
    "Budding Seeds": 7000,
    "Winter's Revenge": 3000,
    "Illustrious Healing": 7000,
}


def _resolved(
    name: str,
    bar: str,
    slot: int,
    tag: HealerRotationTag,
) -> ResolvedHealerSkillPolicy:
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar=bar,
            slot=slot,
            skill_name=name,
            tags=(tag,),
        ),
        ability_id=slot,
    )


def _demand(name: str, start: float, end: float) -> RotationDemandWindow:
    return RotationDemandWindow(
        name=name,
        start_seconds=start,
        end_seconds=end,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=25.0,
        actions=(
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Elemental Ring",
                bar="back",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Budding Seeds",
                bar="front",
            ),
            RotationAction(
                time_seconds=12.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Winter's Revenge",
                bar="back",
            ),
            RotationAction(
                time_seconds=14.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Illustrious Healing",
                bar="front",
            ),
        ),
    )


def _resource_inputs(plan: RotationPlan):
    pool = StaticResourcePool(
        resource=ResourceType.MAGICKA,
        maximum=20000,
        displayed_recovery=0,
    )
    costs = tuple(
        ResourceCostEvent(
            time_seconds=action.time_seconds,
            resource=ResourceType.MAGICKA,
            amount=_COST_BY_SKILL[action.name or ""],
            source=action.name or "",
        )
        for action in plan.actions
        if action.kind is RotationActionKind.SKILL
    )
    replay_inputs = ResourceTimelineReplayInputs(
        pool=pool,
        starting_amount=15000,
        cost_events=costs,
    )
    timeline = run_resource_timeline(
        pool,
        starting_amount=15000,
        cost_events=costs,
    )
    return replay_inputs, timeline


def _cage_one_step(plan: RotationPlan) -> HealerExactSequentialReserveStep:
    replay_inputs, timeline = _resource_inputs(plan)
    demand = _demand("Ice Cage 1", 10.0, 17.0)
    assessment = HealerDemandPolicyAssessment(
        demand=demand,
        protected=(
            _resolved(
                "Budding Seeds",
                "front",
                1,
                HealerRotationTag.BURST_PREPARATION,
            ),
        ),
        discretionary=(
            _resolved(
                "Elemental Ring",
                "back",
                1,
                HealerRotationTag.DISCRETIONARY_FILLER,
            ),
        ),
        neutral=(),
    )
    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=21.0,
        required_spends=(
            RequiredRotationSpend(10.0, "Budding Seeds"),
            RequiredRotationSpend(14.0, "Illustrious Healing"),
        ),
    )
    return HealerExactSequentialReserveStep(
        demand_assessment=assessment,
        timeline=timeline,
        budget=budget,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=5.0,
                source="Elemental Ring",
                delay_order=0,
            ),
        ),
        replay_inputs=replay_inputs,
    )


def _cage_two_step(plan: RotationPlan) -> HealerExactSequentialReserveStep:
    replay_inputs, timeline = _resource_inputs(plan)
    demand = _demand("Ice Cage 2", 14.0, 21.0)
    assessment = HealerDemandPolicyAssessment(
        demand=demand,
        protected=(
            _resolved(
                "Budding Seeds",
                "front",
                1,
                HealerRotationTag.CRITICAL_HEALING,
            ),
            _resolved(
                "Illustrious Healing",
                "front",
                4,
                HealerRotationTag.CRITICAL_HEALING,
            ),
        ),
        discretionary=(
            _resolved(
                "Winter's Revenge",
                "back",
                3,
                HealerRotationTag.DISCRETIONARY_FILLER,
            ),
        ),
        neutral=(),
    )
    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=14.0,
        end_seconds=21.0,
        required_spends=(
            RequiredRotationSpend(14.0, "Illustrious Healing"),
        ),
    )
    return HealerExactSequentialReserveStep(
        demand_assessment=assessment,
        timeline=timeline,
        budget=budget,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=12.0,
                source="Winter's Revenge",
                delay_order=0,
            ),
        ),
        replay_inputs=replay_inputs,
    )


def test_exact_sequential_healer_reserve_carries_adjusted_plan_into_second_cage() -> None:
    original = _plan()
    seen_plans: list[tuple[str, ...]] = []

    def evaluate_step(current: RotationPlan, index: int) -> HealerExactSequentialReserveStep:
        names = tuple(action.name or "" for action in current.actions)
        seen_plans.append(names)
        if index == 0:
            return _cage_one_step(current)

        assert "Elemental Ring" not in names
        assert "Winter's Revenge" in names
        return _cage_two_step(current)

    result = propose_exact_sequential_healer_reserve_decisions(
        plan=original,
        step_count=2,
        evaluate_step=evaluate_step,
    )

    assert len(result.decisions) == 2
    assert result.original_plan is original
    assert seen_plans[0] == (
        "Elemental Ring",
        "Budding Seeds",
        "Winter's Revenge",
        "Illustrious Healing",
    )
    assert seen_plans[1] == (
        "Budding Seeds",
        "Winter's Revenge",
        "Illustrious Healing",
    )

    first, second = result.decisions
    assert first.budget_reserve.requirement.minimum_amount == 14000
    assert first.budget_reserve.assessment.available_before_start == 12000
    assert first.exact_protection.replayed_assessment.available_before_start == 15000
    assert first.exact_protection.replayed_assessment.satisfied is True
    assert [
        item.candidate.source
        for item in first.exact_protection.protection_plan.selected_to_withhold
    ] == ["Elemental Ring"]

    assert second.budget_reserve.requirement.minimum_amount == 7000
    assert second.budget_reserve.assessment.available_before_start == 5000
    assert second.exact_protection.replayed_assessment.available_before_start == 8000
    assert second.exact_protection.replayed_assessment.satisfied is True
    assert [
        item.candidate.source
        for item in second.exact_protection.protection_plan.selected_to_withhold
    ] == ["Winter's Revenge"]

    assert [action.name for action in result.final_plan.actions] == [
        "Budding Seeds",
        "Illustrious Healing",
    ]
    assert [action.name for action in original.actions] == [
        "Elemental Ring",
        "Budding Seeds",
        "Winter's Revenge",
        "Illustrious Healing",
    ]


def test_exact_sequential_healer_reserve_rejects_non_increasing_demand_starts() -> None:
    original = _plan()

    def evaluate_step(current: RotationPlan, _index: int) -> HealerExactSequentialReserveStep:
        return _cage_one_step(current)

    with pytest.raises(ValueError, match="starts must strictly increase"):
        propose_exact_sequential_healer_reserve_decisions(
            plan=original,
            step_count=2,
            evaluate_step=evaluate_step,
        )
