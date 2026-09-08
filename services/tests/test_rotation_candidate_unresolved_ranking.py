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


def _scorecard(*, missing_demand: bool = False, unresolved=()) -> RotationCandidateScorecard:
    class _Requirement:
        pass

    class _Coverage:
        satisfied = not missing_demand
        requirement = _Requirement()

    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(_Coverage(),) if missing_demand else (),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=tuple(unresolved),
    )


def test_candidate_specific_unresolved_counts_as_hard_failure_and_is_explained() -> None:
    one_hard_failure = _scorecard(missing_demand=True)
    two_unresolved_failures = _scorecard(
        unresolved=(
            "canonical action timing unresolved for used action: Skill A",
            "canonical action range unresolved for used action: Skill B",
        )
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("two-unresolved", two_unresolved_failures),
            RotationCandidateRankingInput("one-missing-demand", one_hard_failure),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "one-missing-demand",
        "two-unresolved",
    ]
    assert all(item.tier is RotationCandidateTier.INELIGIBLE for item in ranked)
    assert "candidate-specific unresolved: canonical action timing unresolved for used action: Skill A" in ranked[1].reasons
    assert "candidate-specific unresolved: canonical action range unresolved for used action: Skill B" in ranked[1].reasons
