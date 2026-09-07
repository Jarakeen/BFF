from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_bar_availability import RotationBarAvailabilityWindow
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
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
        duration_seconds=20.0,
        actions=tuple(actions),
    )


def _sustain(ending: int = 20000):
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


def _front_only_window() -> RotationBarAvailabilityWindow:
    return RotationBarAvailabilityWindow(
        name="single-bar encounter state",
        start_seconds=5.0,
        end_seconds=10.0,
        allowed_bars=frozenset({"front"}),
        bar_swaps_allowed=False,
    )


def test_scorecard_marks_other_bar_action_as_hard_failure() -> None:
    baseline = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
    )
    illegal = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
    )

    card = RotationCandidateScorecardService().compare(
        baseline_plan=baseline,
        candidate_plan=illegal,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        bar_availability_windows=(_front_only_window(),),
    )

    assert card.supplied_obligations_satisfied is False
    assert len(card.bar_availability_violations) == 1
    assert card.bar_availability_violations[0].reason == "scheduled action uses an unavailable bar"


def test_legal_candidate_outranks_resource_equal_illegal_candidate() -> None:
    legal_plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
    )
    illegal_plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
    )
    service = RotationCandidateScorecardService()
    legal = service.compare(
        baseline_plan=legal_plan,
        candidate_plan=legal_plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        bar_availability_windows=(_front_only_window(),),
    )
    illegal = service.compare(
        baseline_plan=legal_plan,
        candidate_plan=illegal_plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
        bar_availability_windows=(_front_only_window(),),
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("illegal", illegal),
            RotationCandidateRankingInput("legal", legal),
        )
    )

    assert ranked[0].candidate_id == "legal"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].candidate_id == "illegal"
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("bar-availability" in reason for reason in ranked[1].reasons)
