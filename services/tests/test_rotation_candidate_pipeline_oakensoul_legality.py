from types import SimpleNamespace

from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import GearSlot, PlayerBuild
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
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


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Oak",
        build_name="One Bar",
        duration_seconds=10.0,
        actions=actions,
    )


def _scorecard(plan: RotationPlan) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
        active_bar_assessment=RotationActiveBarAssessor().assess(plan),
    )


def test_pipeline_final_scorecard_rejects_oakensoul_bar_swap():
    plan = _plan(
        RotationAction(1.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(2.0, 1, RotationActionKind.SKILL, "Back Skill", "back"),
    )
    build = PlayerBuild(Ring1=GearSlot(Set="Oakensoul Ring"))
    pipeline = RotationRecoveryHeavyCandidatePipelineService()
    wrapped = pipeline._with_saved_build_bar_access(
        build,
        lambda snapshot: _scorecard(snapshot.plan),
    )

    result = wrapped(SimpleNamespace(plan=plan))

    assert result.active_bar_assessment is not None
    assert result.active_bar_assessment.legal is False
    assert any(
        "Oakensoul Ring prevents swapping" in row.reason
        for row in result.active_bar_assessment.violations
    )


def test_pipeline_final_scorecard_keeps_ordinary_two_bar_plan_legal():
    plan = _plan(
        RotationAction(1.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(2.0, 1, RotationActionKind.SKILL, "Back Skill", "back"),
    )
    pipeline = RotationRecoveryHeavyCandidatePipelineService()
    wrapped = pipeline._with_saved_build_bar_access(
        PlayerBuild(),
        lambda snapshot: _scorecard(snapshot.plan),
    )

    result = wrapped(SimpleNamespace(plan=plan))

    assert result.active_bar_assessment is not None
    assert result.active_bar_assessment.legal is True
    assert result.active_bar_assessment.final_bar == "back"
