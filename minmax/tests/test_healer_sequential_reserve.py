import pytest

from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_reserve_bridge import (
    HealerDiscretionaryAction,
    HealerReserveProtectionBridgeResult,
)
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
)
from minmax.healer_sequential_reserve import (
    HealerSequentialReserveStep,
    propose_sequential_healer_reserve_decisions,
)
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_reserve_priority import ReserveProtectionPriority
from minmax.rotation_reserve_protection import (
    ReserveProtectionCandidate,
    RotationReserveProtectionAnalysis,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)


def _resolved(name: str, bar: str, slot: int) -> ResolvedHealerSkillPolicy:
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar=bar,
            slot=slot,
            skill_name=name,
            tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
        ),
        ability_id=slot,
    )


def _bridge(
    *,
    plan: RotationPlan,
    demand: RotationDemandWindow,
    source: str,
    bar: str,
    amount: int = 2500,
) -> HealerReserveProtectionBridgeResult:
    action = next(item for item in plan.actions if item.name == source)
    resolved = _resolved(source, bar, 1 if source == "Elemental Ring" else 3)
    reserve = RotationResourceReserveAssessment(
        demand=demand,
        requirement=RotationResourceReserveRequirement(
            demand_name=demand.name,
            resource=ResourceType.MAGICKA,
            minimum_amount=16000,
        ),
        available_before_start=14500,
    )
    return HealerReserveProtectionBridgeResult(
        demand_assessment=HealerDemandPolicyAssessment(
            demand=demand,
            protected=(),
            discretionary=(resolved,),
            neutral=(),
        ),
        discretionary_actions=(
            HealerDiscretionaryAction(
                action=action,
                skill_name=source,
                bar=bar,
            ),
        ),
        reserve_analysis=RotationReserveProtectionAnalysis(
            demand=demand,
            reserve_assessment=reserve,
            candidates=(
                ReserveProtectionCandidate(
                    time_seconds=action.time_seconds,
                    source=source,
                    resource=ResourceType.MAGICKA,
                    amount=amount,
                ),
            ),
            recoverable_amount=amount,
            projected_available_if_all_withheld=14500 + amount,
        ),
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=25.0,
        actions=(
            RotationAction(4.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(5.0, 0, RotationActionKind.SKILL, "Elemental Ring", "back"),
            RotationAction(8.0, 0, RotationActionKind.SKILL, "Winter's Revenge", "back"),
        ),
    )


def test_staggered_ice_cages_carry_adjusted_plan_into_second_window() -> None:
    original = _plan()
    cage_one = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    cage_two = RotationDemandWindow(
        name="Ice Cage 2",
        start_seconds=14.0,
        end_seconds=21.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    seen_plans: list[tuple[str | None, ...]] = []

    def evaluate_step(current: RotationPlan, index: int) -> HealerSequentialReserveStep:
        seen_plans.append(tuple(action.name for action in current.actions))
        if index == 0:
            return HealerSequentialReserveStep(
                bridge=_bridge(
                    plan=current,
                    demand=cage_one,
                    source="Elemental Ring",
                    bar="back",
                ),
                priorities=(ReserveProtectionPriority(5.0, "Elemental Ring", 0),),
            )
        assert "Elemental Ring" not in [action.name for action in current.actions]
        return HealerSequentialReserveStep(
            bridge=_bridge(
                plan=current,
                demand=cage_two,
                source="Winter's Revenge",
                bar="back",
            ),
            priorities=(ReserveProtectionPriority(8.0, "Winter's Revenge", 0),),
        )

    result = propose_sequential_healer_reserve_decisions(
        plan=original,
        step_count=2,
        evaluate_step=evaluate_step,
    )

    assert seen_plans == [
        ("Budding Seeds", "Elemental Ring", "Winter's Revenge"),
        ("Budding Seeds", "Winter's Revenge"),
    ]
    assert [decision.bridge.demand_assessment.demand.name for decision in result.decisions] == [
        "Ice Cage 1",
        "Ice Cage 2",
    ]
    assert [action.name for action in result.final_plan.actions] == ["Budding Seeds"]
    assert [action.name for action in original.actions] == [
        "Budding Seeds",
        "Elemental Ring",
        "Winter's Revenge",
    ]


def test_sequential_healer_reserve_allows_overlapping_windows_but_requires_later_start() -> None:
    original = _plan()
    first = RotationDemandWindow(
        name="First",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    same_start = RotationDemandWindow(
        name="Second",
        start_seconds=10.0,
        end_seconds=18.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )

    def evaluate_step(current: RotationPlan, index: int) -> HealerSequentialReserveStep:
        source = "Elemental Ring" if index == 0 else "Winter's Revenge"
        demand = first if index == 0 else same_start
        time_seconds = 5.0 if index == 0 else 8.0
        return HealerSequentialReserveStep(
            bridge=_bridge(plan=current, demand=demand, source=source, bar="back"),
            priorities=(ReserveProtectionPriority(time_seconds, source, 0),),
        )

    with pytest.raises(ValueError, match="strictly increase"):
        propose_sequential_healer_reserve_decisions(
            plan=original,
            step_count=2,
            evaluate_step=evaluate_step,
        )
