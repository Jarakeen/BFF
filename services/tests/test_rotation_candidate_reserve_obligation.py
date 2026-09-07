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
from minmax.rotation_plan import RotationPlan
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Phase 2 healing prep",
        start_seconds=40.0,
        end_seconds=45.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _sustain(*, available_before_demand: int, ending: int | None = None):
    starting = 30_000
    ending_amount = available_before_demand if ending is None else int(ending)
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=starting,
        ending_amount=ending_amount,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=20.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="maintenance",
                before=starting,
                attempted_change=available_before_demand - starting,
                applied_change=available_before_demand - starting,
                after=available_before_demand,
            ),
        ),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def _reserve(minimum: int = 15_000) -> RotationResourceReserveRequirement:
    return RotationResourceReserveRequirement(
        demand_name="Phase 2 healing prep",
        resource=ResourceType.MAGICKA,
        minimum_amount=minimum,
    )


def test_reserve_requirement_can_be_satisfied_as_hard_candidate_obligation() -> None:
    plan = _plan()
    sustain = _sustain(available_before_demand=16_000)

    card = RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        demands=(_demand(),),
        reserve_requirements=(_reserve(),),
    )

    assert len(card.reserve_assessments) == 1
    assert card.reserve_assessments[0].available_before_start == 16_000
    assert card.reserve_assessments[0].satisfied is True
    assert card.failed_reserve_assessments == ()
    assert card.supplied_obligations_satisfied is True


def test_zero_total_shortfall_does_not_excuse_missing_demand_entry_reserve() -> None:
    plan = _plan()
    sustain = _sustain(available_before_demand=14_000, ending=20_000)

    card = RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        demands=(_demand(),),
        reserve_requirements=(_reserve(),),
    )

    assert card.candidate_shortfall == 0
    assert len(card.failed_reserve_assessments) == 1
    assert card.failed_reserve_assessments[0].shortfall == 1_000
    assert card.supplied_obligations_satisfied is False


def test_reserve_requirement_must_reference_a_supplied_demand_window() -> None:
    plan = _plan()
    sustain = _sustain(available_before_demand=16_000)

    with pytest.raises(ValueError, match="reserve requirement references unknown demand"):
        RotationCandidateScorecardService().compare(
            baseline_plan=plan,
            candidate_plan=plan,
            baseline_sustain=sustain,
            candidate_sustain=sustain,
            demands=(),
            reserve_requirements=(_reserve(),),
        )


def test_reserve_satisfying_candidate_outranks_prettier_under_reserved_candidate() -> None:
    plan = _plan()
    baseline_sustain = _sustain(available_before_demand=16_000, ending=16_000)
    safe_sustain = _sustain(available_before_demand=16_000, ending=16_000)
    prettier_but_low = _sustain(available_before_demand=14_000, ending=24_000)
    scorecards = RotationCandidateScorecardService()

    safe = scorecards.compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=baseline_sustain,
        candidate_sustain=safe_sustain,
        demands=(_demand(),),
        reserve_requirements=(_reserve(),),
    )
    low = scorecards.compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=baseline_sustain,
        candidate_sustain=prettier_but_low,
        demands=(_demand(),),
        reserve_requirements=(_reserve(),),
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("prettier-but-under-reserved", low),
            RotationCandidateRankingInput("safe", safe),
        )
    )

    assert [item.candidate_id for item in ranked] == ["safe", "prettier-but-under-reserved"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("resource reserve shortfall 1000" in reason for reason in ranked[1].reasons)
