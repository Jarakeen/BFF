from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_demand_bar_access_service import (
    RotationDemandBarAccessClaim,
    RotationDemandBarAccessService,
)


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Phase 2 healing prep",
        start_seconds=29.13,
        end_seconds=34.13,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(28.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(29.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(30.0, 0, RotationActionKind.SKILL, "Expansive Frost Cloak", "back"),
            RotationAction(31.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(32.0, 0, RotationActionKind.SKILL, "Winter's Revenge", "back"),
            RotationAction(33.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(34.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(35.0, 0, RotationActionKind.BAR_SWAP, bar="front"),
            RotationAction(36.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
        ),
    )


def _sustain():
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=20000,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def test_bar_access_rescue_can_satisfy_demand_without_dropping_displaced_support_work() -> None:
    baseline = _plan()
    demand = _demand()
    rescue = RotationDemandBarAccessService().refine(
        plan=baseline,
        demands=(demand,),
        claim=RotationDemandBarAccessClaim(
            demand_name=demand.name,
            bar="front",
            skill_name="Budding Seeds",
        ),
    )

    assert rescue.applied is True
    names = tuple(
        action.name
        for action in rescue.plan.actions
        if action.kind is RotationActionKind.SKILL
    )
    assert "Budding Seeds" in names
    assert "Expansive Frost Cloak" in names
    assert "Winter's Revenge" in names

    requirement = RotationDemandActionRequirement(
        demand_name=demand.name,
        skill_name="Budding Seeds",
        bar="front",
    )
    scorecards = RotationCandidateScorecardService()
    baseline_card = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=baseline,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        demands=(demand,),
        demand_requirements=(requirement,),
    )
    rescue_card = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=rescue.plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        demands=(demand,),
        demand_requirements=(requirement,),
    )

    assert baseline_card.supplied_obligations_satisfied is False
    assert rescue_card.supplied_obligations_satisfied is True
    assert rescue_card.demand_coverage[0].cast_times == (31.0,)
