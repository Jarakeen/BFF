from minmax.rotation_action_slot_legality import (
    RotationActionSlotAssessor,
    RotationActionSlotRequirement,
)
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


def _plan(kind: RotationActionKind) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(10.0, 0, kind, "Front Ultimate", "front"),
        ),
    )


def _scorecard(plan: RotationPlan) -> RotationCandidateScorecard:
    requirement = RotationActionSlotRequirement(
        "Front Ultimate",
        ("front",),
        action_kind=RotationActionKind.ULTIMATE,
    )
    assessment = RotationActionSlotAssessor().assess(plan, (requirement,))
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
        slot_assessment=assessment,
    )


def test_wrong_saved_slot_action_kind_is_hard_ineligible() -> None:
    illegal = RotationCandidateRankingInput(
        "aaa-wrong-kind",
        _scorecard(_plan(RotationActionKind.SKILL)),
    )
    legal = RotationCandidateRankingInput(
        "zzz-correct-kind",
        _scorecard(_plan(RotationActionKind.ULTIMATE)),
    )

    ranked = RotationCandidateRankingService().rank((illegal, legal))

    assert ranked[0].candidate_id == "zzz-correct-kind"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].candidate_id == "aaa-wrong-kind"
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("action slot violation" in reason for reason in ranked[1].reasons)
    assert any(
        "scheduled action kind does not match the saved-build slot kind" in reason
        for reason in ranked[1].reasons
    )
