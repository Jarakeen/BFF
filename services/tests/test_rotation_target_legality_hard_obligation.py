from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_hard_obligation_state_service import (
    RotationCandidateHardObligationStateService,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _sustain():
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=30000,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            timeline=timeline,
            action_cost_events=(),
        ),
        unresolved=(),
    )


def _scorecard(target_kind: RotationTargetKind):
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    return RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        target_requirements=(
            RotationActionTargetRequirement(
                allowed_targets=(RotationTargetKind.ALLY,),
                action_name="Combat Prayer",
                action_kind=RotationActionKind.SKILL,
                bar="front",
            ),
        ),
        target_state_windows=(
            RotationTargetStateWindow(
                "Known target",
                9.0,
                11.0,
                target_kind,
            ),
        ),
    )


def test_target_mismatch_is_first_class_scorecard_hard_failure() -> None:
    scorecard = _scorecard(RotationTargetKind.ENEMY)

    assert len(scorecard.target_violations) == 1
    assert scorecard.target_violations[0].observed_target is RotationTargetKind.ENEMY
    assert not scorecard.supplied_obligations_satisfied
    assert scorecard.candidate_specific_unresolved == ()


def test_target_mismatch_ranks_ineligible_with_explicit_reason() -> None:
    legal = _scorecard(RotationTargetKind.ALLY)
    illegal = _scorecard(RotationTargetKind.ENEMY)

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("illegal", illegal),
            RotationCandidateRankingInput("legal", legal),
        )
    )

    assert ranked[0].candidate_id == "legal"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("1 action target violation" in reason for reason in ranked[1].reasons)
    assert any(
        "observed enemy, allowed ally" in reason
        for reason in ranked[1].reasons
    )


def test_target_mismatch_participates_in_fixed_point_hard_state() -> None:
    scorecard = _scorecard(RotationTargetKind.ENEMY)

    state = RotationCandidateHardObligationStateService().from_scorecard(scorecard)

    assert any(
        token.startswith("target_legality|Combat Prayer|skill|front|10|Known target|enemy|ally")
        for token in state
    )
