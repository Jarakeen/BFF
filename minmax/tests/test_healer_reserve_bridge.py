import pytest

from minmax.healer_demand_policy import HealerDemandPolicyAssessment
from minmax.healer_reserve_bridge import analyze_healer_reserve_protection
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
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)


def _resolved(
    *,
    bar: str,
    slot: int,
    name: str,
    tags: tuple[HealerRotationTag, ...],
) -> ResolvedHealerSkillPolicy:
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar=bar,
            slot=slot,
            skill_name=name,
            tags=tags,
        ),
        ability_id=slot,
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _demand_assessment() -> HealerDemandPolicyAssessment:
    demand = _demand()
    return HealerDemandPolicyAssessment(
        demand=demand,
        protected=(
            _resolved(
                bar="front",
                slot=1,
                name="Budding Seeds",
                tags=(
                    HealerRotationTag.CRITICAL_HEALING,
                    HealerRotationTag.BURST_PREPARATION,
                ),
            ),
        ),
        discretionary=(
            _resolved(
                bar="back",
                slot=1,
                name="Elemental Ring",
                tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
            ),
        ),
        neutral=(
            _resolved(
                bar="front",
                slot=3,
                name="Combat Prayer",
                tags=(HealerRotationTag.SUPPORT_MAINTENANCE,),
            ),
        ),
    )


def _reserve_assessment() -> RotationResourceReserveAssessment:
    demand = _demand()
    return RotationResourceReserveAssessment(
        demand=demand,
        requirement=RotationResourceReserveRequirement(
            demand_name=demand.name,
            resource=ResourceType.MAGICKA,
            minimum_amount=16000,
        ),
        available_before_start=14500,
    )


def _timeline() -> ResourceTimelineResult:
    return ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=20000,
        ending_amount=14500,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=5.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Budding Seeds",
                before=20000,
                attempted_change=-2000,
                applied_change=-2000,
                after=18000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=7.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Elemental Ring",
                before=18000,
                attempted_change=-2500,
                applied_change=-2500,
                after=15500,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=8.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Combat Prayer",
                before=15500,
                attempted_change=-1000,
                applied_change=-1000,
                after=14500,
            ),
        ),
    )


def test_healer_reserve_bridge_nominates_only_policy_discretionary_casts() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(5.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(7.0, 0, RotationActionKind.SKILL, "Elemental Ring", "back"),
            RotationAction(8.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
        ),
    )

    result = analyze_healer_reserve_protection(
        plan=plan,
        demand_assessment=_demand_assessment(),
        timeline=_timeline(),
        reserve_assessment=_reserve_assessment(),
    )

    assert [item.skill_name for item in result.discretionary_actions] == ["Elemental Ring"]
    assert [item.bar for item in result.discretionary_actions] == ["back"]
    assert [item.source for item in result.reserve_analysis.candidates] == ["Elemental Ring"]
    assert result.reserve_analysis.recoverable_amount == 2500
    assert result.reserve_analysis.projected_available_if_all_withheld == 17000
    assert result.reserve_analysis.can_repair_shortfall is True


def test_healer_reserve_bridge_requires_explicit_bar_context_before_demand() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(7.0, 0, RotationActionKind.SKILL, "Elemental Ring"),
        ),
    )

    with pytest.raises(ValueError, match="explicit bar context"):
        analyze_healer_reserve_protection(
            plan=plan,
            demand_assessment=_demand_assessment(),
            timeline=_timeline(),
            reserve_assessment=_reserve_assessment(),
        )
