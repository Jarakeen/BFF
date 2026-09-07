"""Regression coverage for the audited 2.0m-DPS Xalvakka healer tradeoff.

These values describe the established audit result, not universal Xalvakka
strategy: the bar-access rescue places Budding Seeds at 31 seconds, costs 1,993
Magicka, enters the mechanic window with 20,295 Magicka, and changes Winter's
Revenge duration coverage from 85.00% to 83.33% over the 60-second projection.
"""

from types import SimpleNamespace

import pytest

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
from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastSummary
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_runtime_uptime_service import (
    RotationRuntimeUptimeObjective,
    RotationRuntimeUptimeRequirement,
)


_DEMAND_NAME = "Xalvakka Phase 2 healing prep"


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name=_DEMAND_NAME,
        start_seconds=29.1349536,
        end_seconds=34.1349536,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _plan(*, budding_seeds_inside_demand: bool) -> RotationPlan:
    actions = ()
    if budding_seeds_inside_demand:
        actions = (
            RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, bar="front"),
            RotationAction(31.0, 1, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(32.0, 2, RotationActionKind.BAR_SWAP, bar="back"),
        )
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=actions,
    )


def _sustain(*, before_demand: int, ending: int):
    starting = 30_000
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=starting,
        ending_amount=ending,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=20.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="pre-mechanic rotation",
                before=starting,
                attempted_change=before_demand - starting,
                applied_change=before_demand - starting,
                after=before_demand,
            ),
        ),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def _duration(uptime: float) -> RotationDurationProjection:
    return RotationDurationProjection(
        analysis=RotationRecastAnalysis(
            windows=(),
            summaries=(
                RotationRecastSummary(
                    skill_name="Winter's Revenge",
                    bar="back",
                    duration_seconds=12.0,
                    cast_count=5,
                    active_seconds=60.0 * uptime,
                    uptime_fraction=uptime,
                    total_gap_seconds=60.0 * (1.0 - uptime),
                    total_premature_seconds=0.0,
                ),
            ),
        ),
        rules=(),
        unresolved=(),
    )


def _cards(*, minimum_uptime: float | None):
    baseline_plan = _plan(budding_seeds_inside_demand=False)
    rescue_plan = _plan(budding_seeds_inside_demand=True)
    baseline_sustain = _sustain(before_demand=22_288, ending=22_000)
    rescue_sustain = _sustain(before_demand=20_295, ending=20_007)
    demand = _demand()
    action_requirement = RotationDemandActionRequirement(
        demand_name=demand.name,
        skill_name="Budding Seeds",
        bar="front",
    )
    reserve_requirement = RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=ResourceType.MAGICKA,
        minimum_amount=16_000,
    )
    uptime_requirements = (
        ()
        if minimum_uptime is None
        else (
            RotationRuntimeUptimeRequirement(
                skill_name="Winter's Revenge",
                bar="back",
                minimum_uptime=minimum_uptime,
            ),
        )
    )
    objective = RotationRuntimeUptimeObjective("Winter's Revenge", "back")
    scorecards = RotationCandidateScorecardService()

    common = {
        "baseline_plan": baseline_plan,
        "baseline_sustain": baseline_sustain,
        "demands": (demand,),
        "demand_requirements": (action_requirement,),
        "reserve_requirements": (reserve_requirement,),
        "runtime_uptime_requirements": uptime_requirements,
        "runtime_uptime_objective": objective,
    }
    baseline = scorecards.compare(
        **common,
        candidate_plan=baseline_plan,
        candidate_sustain=baseline_sustain,
        candidate_duration=_duration(0.85),
    )
    mechanic_claim = scorecards.compare(
        **common,
        candidate_plan=baseline_plan,
        candidate_sustain=baseline_sustain,
        candidate_duration=_duration(0.85),
    )
    rescue = scorecards.compare(
        **common,
        candidate_plan=rescue_plan,
        candidate_sustain=rescue_sustain,
        candidate_duration=_duration(5.0 / 6.0),
    )
    return baseline, mechanic_claim, rescue


def _rank(*, minimum_uptime: float | None):
    baseline, mechanic_claim, rescue = _cards(minimum_uptime=minimum_uptime)
    return RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("baseline", baseline),
            RotationCandidateRankingInput("mechanic-claim", mechanic_claim),
            RotationCandidateRankingInput("bar-access-rescue", rescue),
        )
    )


def test_bar_access_rescue_wins_when_no_uptime_floor_is_invented() -> None:
    ranked = _rank(minimum_uptime=None)

    assert [item.candidate_id for item in ranked] == [
        "bar-access-rescue",
        "baseline",
        "mechanic-claim",
    ]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[0].scorecard.demand_coverage[0].cast_times == (31.0,)
    assert ranked[0].scorecard.reserve_assessments[0].available_before_start == 20_295
    assert ranked[0].scorecard.runtime_uptime_objective_assessment is not None
    assert ranked[0].scorecard.runtime_uptime_objective_assessment.observed_uptime == pytest.approx(
        5.0 / 6.0
    )
    assert ranked[0].scorecard.consequence.ending_resource_delta == -1_993


def test_higher_winters_revenge_uptime_cannot_excuse_missing_budding_seeds() -> None:
    ranked = _rank(minimum_uptime=None)

    rescue, baseline = ranked[0], ranked[1]
    assert rescue.scorecard.runtime_uptime_objective_assessment.observed_uptime < (
        baseline.scorecard.runtime_uptime_objective_assessment.observed_uptime
    )
    assert rescue.tier is RotationCandidateTier.ELIGIBLE
    assert baseline.tier is RotationCandidateTier.INELIGIBLE
    assert any("missing 1 explicit demand" in reason for reason in baseline.reasons)


def test_caller_supplied_84_percent_floor_exposes_no_fully_eligible_candidate() -> None:
    ranked = _rank(minimum_uptime=0.84)

    assert all(item.tier is RotationCandidateTier.INELIGIBLE for item in ranked)
    rescue = next(item for item in ranked if item.candidate_id == "bar-access-rescue")
    assert rescue.scorecard.demand_coverage[0].satisfied is True
    assert rescue.scorecard.reserve_assessments[0].satisfied is True
    assert rescue.scorecard.failed_runtime_uptime_assessments[0].observed_uptime == pytest.approx(
        5.0 / 6.0
    )
    assert any(
        "observed 83.33%, required 84.00%" in reason
        for reason in rescue.reasons
    )
