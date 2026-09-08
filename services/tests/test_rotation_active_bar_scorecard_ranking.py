from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
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


def _scorecard(plan: RotationPlan) -> RotationCandidateScorecard:
    assessment = RotationActiveBarAssessor().assess(plan, initial_bar="front")
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
        active_bar_assessment=assessment,
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=actions,
    )


def test_wrong_active_bar_is_hard_ineligible_even_when_candidate_id_would_win_tie() -> None:
    illegal = RotationCandidateRankingInput(
        "aaa-illegal",
        _scorecard(
            _plan(
                RotationAction(10.0, 0, RotationActionKind.SKILL, "Back Heal", "back"),
            )
        ),
    )
    legal = RotationCandidateRankingInput(
        "zzz-legal",
        _scorecard(
            _plan(
                RotationAction(9.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
                RotationAction(10.0, 0, RotationActionKind.SKILL, "Back Heal", "back"),
            )
        ),
    )

    ranked = RotationCandidateRankingService().rank((illegal, legal))

    assert ranked[0].candidate_id == "zzz-legal"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].candidate_id == "aaa-illegal"
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("active-bar violation" in reason for reason in ranked[1].reasons)
    assert any(
        "scheduled back bar, active front bar" in reason
        for reason in ranked[1].reasons
    )
