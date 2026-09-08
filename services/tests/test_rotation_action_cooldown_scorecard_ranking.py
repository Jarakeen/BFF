from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_action_cooldown import RotationActionCooldownRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService


def _plan(second_cast: float) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
            RotationAction(second_cast, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
        ),
    )


def _sustain():
    timeline = SimpleNamespace(
        starting_amount=20_000,
        ending_amount=20_000,
        total_shortfall=0,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def test_cooldown_illegal_candidate_is_ineligible_and_cannot_win_soft_tie() -> None:
    baseline = _plan(15.0)
    legal = _plan(15.0)
    illegal = _plan(14.0)
    sustain = _sustain()
    requirement = RotationActionCooldownRequirement(
        action_name="Role Neutral Proc",
        cooldown_seconds=5.0,
    )
    scorecards = RotationCandidateScorecardService()

    legal_scorecard = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=legal,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        cooldown_requirements=(requirement,),
    )
    illegal_scorecard = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=illegal,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        cooldown_requirements=(requirement,),
    )

    assert legal_scorecard.supplied_obligations_satisfied
    assert not legal_scorecard.cooldown_violations
    assert not illegal_scorecard.supplied_obligations_satisfied
    assert len(illegal_scorecard.cooldown_violations) == 1

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("a-illegal", illegal_scorecard),
            RotationCandidateRankingInput("z-legal", legal_scorecard),
        )
    )

    assert [item.candidate_id for item in ranked] == ["z-legal", "a-illegal"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("1 action cooldown violation(s)" in reason for reason in ranked[1].reasons)
    assert any(
        "cooldown legality for 'Role Neutral Proc' at 14s: interval 4s, required 5s" in reason
        for reason in ranked[1].reasons
    )
