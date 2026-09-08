from __future__ import annotations

from minmax.rotation_action_range import (
    RotationActionRangeAssessment,
    RotationActionRangeRequirement,
    RotationActionRangeViolation,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _consequence() -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
    )


def _scorecard(*, range_assessment=None) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
        range_assessment=range_assessment,
    )


def test_range_violation_is_hard_obligation_and_reason_is_explicit() -> None:
    requirement = RotationActionRangeRequirement(
        action_name="Ranged Heal",
        minimum_range=0.0,
        maximum_range=28.0,
    )
    violation = RotationActionRangeViolation(
        requirement=requirement,
        window_name="Cage rescue",
        time_seconds=42.0,
        distance=32.0,
        minimum_range=0.0,
        maximum_range=28.0,
    )
    illegal = _scorecard(
        range_assessment=RotationActionRangeAssessment((violation,)),
    )
    legal = _scorecard()

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("aaa-out-of-range", illegal),
            RotationCandidateRankingInput("zzz-legal", legal),
        )
    )

    assert [item.candidate_id for item in ranked] == ["zzz-legal", "aaa-out-of-range"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert not illegal.supplied_obligations_satisfied
    text = " ".join(ranked[1].reasons)
    assert "1 action range violation(s)" in text
    assert "'Ranged Heal'" in text
    assert "distance 32" in text
    assert "legal range 0..28" in text
    assert "outside" in text
