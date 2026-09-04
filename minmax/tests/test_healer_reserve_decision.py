from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_reserve_bridge import (
    HealerDiscretionaryAction,
    HealerReserveProtectionBridgeResult,
)
from minmax.healer_reserve_decision import propose_healer_reserve_decision
from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
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


def _resolved(name: str, bar: str, slot: int, tag: HealerRotationTag) -> ResolvedHealerSkillPolicy:
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar=bar,
            slot=slot,
            skill_name=name,
            tags=(tag,),
        ),
        ability_id=slot,
    )


def test_healer_reserve_decision_withholds_only_needed_discretionary_cast() -> None:
    demand = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    protected = _resolved(
        "Budding Seeds",
        "front",
        1,
        HealerRotationTag.BURST_PREPARATION,
    )
    discretionary_one = _resolved(
        "Elemental Ring",
        "back",
        1,
        HealerRotationTag.DISCRETIONARY_FILLER,
    )
    discretionary_two = _resolved(
        "Winter's Revenge",
        "back",
        3,
        HealerRotationTag.DISCRETIONARY_FILLER,
    )
    demand_assessment = HealerDemandPolicyAssessment(
        demand=demand,
        protected=(protected,),
        discretionary=(discretionary_one, discretionary_two),
        neutral=(),
    )

    protected_cast = RotationAction(
        time_seconds=4.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Budding Seeds",
        bar="front",
    )
    filler_one = RotationAction(
        time_seconds=5.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Elemental Ring",
        bar="back",
    )
    filler_two = RotationAction(
        time_seconds=8.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Winter's Revenge",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(protected_cast, filler_one, filler_two),
    )

    reserve_requirement = RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=ResourceType.MAGICKA,
        minimum_amount=16000,
    )
    reserve_assessment = RotationResourceReserveAssessment(
        demand=demand,
        requirement=reserve_requirement,
        available_before_start=14500,
    )
    candidates = (
        ReserveProtectionCandidate(
            time_seconds=5.0,
            source="Elemental Ring",
            resource=ResourceType.MAGICKA,
            amount=2500,
        ),
        ReserveProtectionCandidate(
            time_seconds=8.0,
            source="Winter's Revenge",
            resource=ResourceType.MAGICKA,
            amount=3000,
        ),
    )
    bridge = HealerReserveProtectionBridgeResult(
        demand_assessment=demand_assessment,
        discretionary_actions=(
            HealerDiscretionaryAction(
                action=filler_one,
                skill_name="Elemental Ring",
                bar="back",
            ),
            HealerDiscretionaryAction(
                action=filler_two,
                skill_name="Winter's Revenge",
                bar="back",
            ),
        ),
        reserve_analysis=RotationReserveProtectionAnalysis(
            demand=demand,
            reserve_assessment=reserve_assessment,
            candidates=candidates,
            recoverable_amount=5500,
            projected_available_if_all_withheld=20000,
        ),
    )

    result = propose_healer_reserve_decision(
        plan=plan,
        bridge=bridge,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=5.0,
                source="Elemental Ring",
                delay_order=0,
            ),
            ReserveProtectionPriority(
                time_seconds=8.0,
                source="Winter's Revenge",
                delay_order=1,
            ),
        ),
    )

    assert result.protection_plan.reserve_repaired is True
    assert [item.candidate.source for item in result.protection_plan.selected_to_withhold] == [
        "Elemental Ring"
    ]
    assert result.adjustment.original_plan is plan
    assert [item.candidate_source for item in result.adjustment.withheld_actions] == [
        "Elemental Ring"
    ]
    assert [(item.name, item.time_seconds) for item in result.adjustment.adjusted_plan.actions] == [
        ("Budding Seeds", 4.0),
        ("Winter's Revenge", 8.0),
    ]
    assert [(item.name, item.time_seconds) for item in plan.actions] == [
        ("Budding Seeds", 4.0),
        ("Elemental Ring", 5.0),
        ("Winter's Revenge", 8.0),
    ]
