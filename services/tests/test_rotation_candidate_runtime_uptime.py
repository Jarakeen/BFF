from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_plan import RotationPlan
from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastSummary
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_runtime_uptime_service import RotationRuntimeUptimeRequirement


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )


def _sustain(*, ending: int):
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=ending,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def _duration(*, skill: str = "Winter's Revenge", uptime: float = 0.9, bar="back"):
    summary = RotationRecastSummary(
        skill_name=skill,
        bar=bar,
        duration_seconds=12.0,
        cast_count=5,
        active_seconds=60.0 * uptime,
        uptime_fraction=uptime,
        total_gap_seconds=60.0 * (1.0 - uptime),
        total_premature_seconds=0.0,
    )
    return RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=(summary,)),
        rules=(),
        unresolved=(),
    )


def _card(*, uptime: float, ending: int = 20000):
    plan = _plan()
    return RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(ending=20000),
        candidate_sustain=_sustain(ending=ending),
        candidate_duration=_duration(uptime=uptime),
        runtime_uptime_requirements=(
            RotationRuntimeUptimeRequirement(
                skill_name="Winter's Revenge",
                bar="back",
                minimum_uptime=0.9,
            ),
        ),
    )


def test_explicit_runtime_uptime_floor_is_a_hard_obligation() -> None:
    passing = _card(uptime=0.9)
    failing = _card(uptime=0.899)

    assert passing.runtime_uptime_assessments[0].satisfied is True
    assert passing.supplied_obligations_satisfied is True
    assert failing.runtime_uptime_assessments[0].shortfall == pytest.approx(0.001)
    assert failing.supplied_obligations_satisfied is False


def test_missing_duration_evidence_fails_closed() -> None:
    plan = _plan()
    empty = RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=()),
        rules=(),
        unresolved=("canonical duration unavailable",),
    )
    card = RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(ending=20000),
        candidate_sustain=_sustain(ending=20000),
        candidate_duration=empty,
        runtime_uptime_requirements=(
            RotationRuntimeUptimeRequirement("Major Courage source", 0.8),
        ),
    )

    assessment = card.failed_runtime_uptime_assessments[0]
    assert assessment.observed_uptime is None
    assert assessment.unresolved == (
        "runtime uptime evidence missing for 'Major Courage source'",
    )
    assert card.supplied_obligations_satisfied is False


def test_uptime_requirement_needs_explicit_duration_evidence() -> None:
    plan = _plan()
    with pytest.raises(ValueError, match="candidate duration evidence"):
        RotationCandidateScorecardService().compare(
            baseline_plan=plan,
            candidate_plan=plan,
            baseline_sustain=_sustain(ending=20000),
            candidate_sustain=_sustain(ending=20000),
            runtime_uptime_requirements=(
                RotationRuntimeUptimeRequirement("Winter's Revenge", 0.9),
            ),
        )


@pytest.mark.parametrize("minimum", [-0.01, 1.01, float("nan")])
def test_uptime_requirement_rejects_invalid_thresholds(minimum: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        RotationRuntimeUptimeRequirement("Winter's Revenge", minimum)


def test_resource_gain_cannot_outrank_required_runtime_uptime() -> None:
    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput(
                "more-magicka-but-uptime-gap",
                _card(uptime=0.85, ending=25000),
            ),
            RotationCandidateRankingInput(
                "meets-uptime",
                _card(uptime=0.9, ending=19000),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "meets-uptime",
        "more-magicka-but-uptime-gap",
    ]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("observed 85.00%, required 90.00%" in reason for reason in ranked[1].reasons)
