from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
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


def test_occupancy_violation_is_hard_candidate_obligation() -> None:
    baseline = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Channeled Skill", "front"),
        RotationAction(12.0, 0, RotationActionKind.SKILL, "Followup Skill", "front"),
    )
    legal = baseline
    illegal = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Channeled Skill", "front"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, "Followup Skill", "front"),
    )
    sustain = _sustain()
    requirement = RotationActionOccupancyRequirement("Channeled Skill", 2.0)
    scorecards = RotationCandidateScorecardService()

    legal_scorecard = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=legal,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        occupancy_requirements=(requirement,),
    )
    illegal_scorecard = scorecards.compare(
        baseline_plan=baseline,
        candidate_plan=illegal,
        baseline_sustain=sustain,
        candidate_sustain=sustain,
        occupancy_requirements=(requirement,),
    )

    ranked = RotationCandidateRankingService().rank(
        (
            RotationCandidateRankingInput("a-illegal-overlap", illegal_scorecard),
            RotationCandidateRankingInput("z-legal-boundary", legal_scorecard),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "z-legal-boundary",
        "a-illegal-overlap",
    ]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert len(illegal_scorecard.occupancy_violations) == 1
    assert any("action occupancy violation" in reason for reason in ranked[1].reasons)
    assert any(
        "'Followup Skill' scheduled at 11s" in reason
        for reason in ranked[1].reasons
    )
