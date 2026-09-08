from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_saved_build_action_range_service import RotationSavedBuildActionRangeEvidence
from services.rotation_saved_build_action_slot_service import RotationSavedBuildActionSlotEvidence
from services.rotation_saved_build_action_timing_service import RotationSavedBuildActionTimingEvidence
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=object(), unresolved=())


class _EvidenceService:
    def __init__(self, evidence) -> None:
        self.evidence = evidence

    def resolve(self, player_build):
        return self.evidence


class _Pipeline:
    def __init__(self, final_plan: RotationPlan) -> None:
        self.final_plan = final_plan
        self.scorecard = None

    def run_effects(self, **kwargs):
        snapshot = SimpleNamespace(candidate_id="slot-candidate", plan=self.final_plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(
                candidate_id="slot-candidate",
                reasons=("all tracked hard obligations satisfied",),
            )
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(
                SimpleNamespace(
                    candidate_id="slot-candidate",
                    reasons=(
                        "all tracked hard obligations satisfied"
                        if selected is not None
                        else "saved-build slot legality failed"
                    ,),
                ),
            ),
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


def _scorecard(_snapshot) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _plan(bar: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Front Heal", bar),
        ),
    )


def _support(pipeline: _Pipeline) -> RotationCanonicalCandidateSupport:
    return RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=_EvidenceService(RotationSavedBuildActionTimingEvidence()),
        action_range_service=_EvidenceService(RotationSavedBuildActionRangeEvidence()),
        action_slot_service=_EvidenceService(
            RotationSavedBuildActionSlotEvidence(
                slot_requirements=(
                    RotationActionSlotRequirement("Front Heal", ("front",)),
                )
            )
        ),
    )


def _run(support: RotationCanonicalCandidateSupport, plan: RotationPlan):
    return support.run_effects(
        player_build=object(),
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )


def test_canonical_candidate_rejects_final_plan_cast_on_unslotted_bar() -> None:
    pipeline = _Pipeline(_plan("back"))
    result = _run(_support(pipeline), pipeline.final_plan)

    assert pipeline.scorecard is not None
    assert len(pipeline.scorecard.slot_violations) == 1
    assert not pipeline.scorecard.supplied_obligations_satisfied
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is False
    assert result.validation.selected_candidate_id is None


def test_canonical_candidate_accepts_final_plan_cast_on_slotted_bar() -> None:
    pipeline = _Pipeline(_plan("front"))
    result = _run(_support(pipeline), pipeline.final_plan)

    assert pipeline.scorecard.slot_violations == ()
    assert pipeline.scorecard.supplied_obligations_satisfied
    assert result.validation.selectable is True
    assert result.validation.selected_candidate_id == "slot-candidate"
