from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import RotationPlanConsequenceService


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
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
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=(),
    )


def _scorecard(consequence) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=consequence,
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def test_heavy_attack_burden_is_exposed_but_does_not_change_ranking_by_itself() -> None:
    baseline = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    no_extra_heavy = baseline
    extra_heavy = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(30.0, 0, RotationActionKind.HEAVY_ATTACK, None, "front"),
    )
    sustain = _sustain()
    service = RotationPlanConsequenceService()

    no_extra_consequence = service.compare(
        baseline_plan=baseline,
        candidate_plan=no_extra_heavy,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
    )
    extra_consequence = service.compare(
        baseline_plan=baseline,
        candidate_plan=extra_heavy,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
    )

    assert no_extra_consequence.candidate_heavy_attacks == 0
    assert no_extra_consequence.heavy_attack_delta == 0
    assert extra_consequence.baseline_heavy_attacks == 0
    assert extra_consequence.candidate_heavy_attacks == 1
    assert extra_consequence.heavy_attack_delta == 1

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("z-no-extra-heavy", _scorecard(no_extra_consequence)),
            RotationCandidateRankingInput("a-extra-heavy", _scorecard(extra_consequence)),
        )
    )

    # Heavy-attack count is diagnostic only. With every ranked signal tied,
    # stable candidate-id ordering still decides the result.
    assert [item.candidate_id for item in ranked] == [
        "a-extra-heavy",
        "z-no-extra-heavy",
    ]
    assert any(
        "heavy-attack burden: candidate 1, delta +1; diagnostic only" in reason
        for reason in ranked[0].reasons
    )
