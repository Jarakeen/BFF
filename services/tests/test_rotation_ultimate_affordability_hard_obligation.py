from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_ultimate_affordability import RotationUltimateAffordabilityRequirement
from minmax.ultimate_resource_timeline import UltimateSpendRule
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
        duration_seconds=60.0,
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
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def _scorecard(*, starting_ultimate: float):
    plan = _plan(
        RotationAction(
            10.0,
            0,
            RotationActionKind.ULTIMATE,
            "Aggressive Horn",
            "front",
        ),
    )
    return RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        ultimate_affordability_requirement=RotationUltimateAffordabilityRequirement(
            starting_amount=starting_ultimate,
            spend_rules=(UltimateSpendRule("Aggressive Horn", 250.0),),
        ),
    )


def test_scorecard_treats_unaffordable_ultimate_as_known_hard_failure() -> None:
    scorecard = _scorecard(starting_ultimate=50.0)

    assert len(scorecard.ultimate_affordability_violations) == 1
    violation = scorecard.ultimate_affordability_violations[0]
    assert violation.action_name == "Aggressive Horn"
    assert violation.balance_before == 50.0
    assert violation.required_cost == 250.0
    assert violation.shortfall == 200.0
    assert scorecard.candidate_specific_unresolved == ()
    assert scorecard.supplied_obligations_satisfied is False


def test_ranking_counts_and_explains_ultimate_affordability_hard_failure() -> None:
    unaffordable = _scorecard(starting_ultimate=50.0)
    affordable = _scorecard(starting_ultimate=250.0)

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("unaffordable", unaffordable),
            RotationCandidateRankingInput("affordable", affordable),
        )
    )

    assert ranked[0].candidate_id == "affordable"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].candidate_id == "unaffordable"
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("1 Ultimate affordability violation" in reason for reason in ranked[1].reasons)
    assert any(
        "Ultimate affordability for 'Aggressive Horn' at 10s" in reason
        and "balance 50" in reason
        and "cost 250" in reason
        and "shortfall 200" in reason
        for reason in ranked[1].reasons
    )


def test_fixed_point_state_tracks_ultimate_affordability_violation() -> None:
    state = RotationCandidateHardObligationStateService().from_scorecard(
        _scorecard(starting_ultimate=50.0)
    )

    assert state == (
        "ultimate_affordability|Aggressive Horn|10|50|250|200",
    )
