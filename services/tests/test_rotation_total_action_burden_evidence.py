from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationPlanConsequenceService,
    RotationResourceConsequenceKind,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=tuple(actions),
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
        unresolved=(),
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
    )


def _scorecard(consequence: RotationPlanConsequence) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=consequence,
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def test_consequence_exposes_total_action_burden_from_actual_plans() -> None:
    baseline = _plan(
        RotationAction(2.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    candidate = _plan(
        RotationAction(2.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(4.0, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        RotationAction(6.0, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
    )

    assert result.baseline_total_actions == 1
    assert result.candidate_total_actions == 3
    assert result.total_actions_delta == 2


def test_total_action_burden_is_reported_but_does_not_change_ranking() -> None:
    more_actions = RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
        baseline_total_actions=1,
        candidate_total_actions=5,
        total_actions_delta=4,
    )
    fewer_actions = RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
        baseline_total_actions=1,
        candidate_total_actions=1,
        total_actions_delta=0,
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("alpha-more-actions", _scorecard(more_actions)),
            RotationCandidateRankingInput("zulu-fewer-actions", _scorecard(fewer_actions)),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "alpha-more-actions",
        "zulu-fewer-actions",
    ]
    assert any(
        "total action burden: candidate 5, delta +4; diagnostic only" in reason
        for reason in ranked[0].reasons
    )
