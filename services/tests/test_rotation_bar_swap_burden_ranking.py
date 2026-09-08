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


def _sustain() -> SimpleNamespace:
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


def _scorecard(consequence) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=consequence,
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def test_consequence_exposes_actual_bar_swap_burden() -> None:
    baseline = _plan(
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(20.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
    )
    candidate = _plan(
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(20.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
        RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(40.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
    )

    assert result.baseline_bar_swaps == 2
    assert result.candidate_bar_swaps == 4
    assert result.bar_swap_delta == 2


def test_fewer_bar_swaps_break_only_the_final_soft_tie() -> None:
    baseline = _plan()
    low_swap_plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(20.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
    )
    high_swap_plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(20.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
        RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(40.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
    )
    service = RotationPlanConsequenceService()
    low_swap = _scorecard(
        service.compare(
            baseline_plan=baseline,
            candidate_plan=low_swap_plan,
            baseline_sustain=_sustain(),
            candidate_sustain=_sustain(),
        )
    )
    high_swap = _scorecard(
        service.compare(
            baseline_plan=baseline,
            candidate_plan=high_swap_plan,
            baseline_sustain=_sustain(),
            candidate_sustain=_sustain(),
        )
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("high-swap", high_swap),
            RotationCandidateRankingInput("low-swap", low_swap),
        )
    )

    assert [item.candidate_id for item in ranked] == ["low-swap", "high-swap"]
    assert any(
        "bar-swap burden: candidate 2, delta +2" in reason
        for reason in ranked[0].reasons
    )
