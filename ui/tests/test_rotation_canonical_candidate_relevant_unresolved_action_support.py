from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_action_range import RotationTargetDistanceWindow
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
        snapshot = SimpleNamespace(candidate_id="candidate", plan=self.final_plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(candidate_id="candidate", reasons=("eligible",))
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(
                SimpleNamespace(
                    candidate_id="candidate",
                    reasons=("eligible" if selected is not None else "ineligible",),
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


def _plan(action_name: str = "Used Skill") -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, action_name, "front"),
        ),
    )


def _support(
    pipeline: _Pipeline,
    *,
    timing: RotationSavedBuildActionTimingEvidence | None = None,
    range_evidence: RotationSavedBuildActionRangeEvidence | None = None,
) -> RotationCanonicalCandidateSupport:
    return RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=_EvidenceService(timing or RotationSavedBuildActionTimingEvidence()),
        action_range_service=_EvidenceService(range_evidence or RotationSavedBuildActionRangeEvidence()),
        action_slot_service=_EvidenceService(RotationSavedBuildActionSlotEvidence()),
    )


def _run(
    support: RotationCanonicalCandidateSupport,
    plan: RotationPlan,
    *,
    target_distance_windows=(),
):
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
        target_distance_windows=target_distance_windows,
    )


def test_used_action_with_unresolved_timing_becomes_candidate_specific_hard_failure() -> None:
    plan = _plan()
    pipeline = _Pipeline(plan)
    support = _support(
        pipeline,
        timing=RotationSavedBuildActionTimingEvidence(
            unresolved=("timing ambiguity",),
            unresolved_action_names=("Used Skill",),
        ),
    )

    result = _run(support, plan)

    assert pipeline.scorecard.candidate_specific_unresolved == (
        "canonical action timing unresolved for used action: Used Skill",
    )
    assert not pipeline.scorecard.supplied_obligations_satisfied
    assert result.validation.selectable is False


def test_unused_action_with_unresolved_timing_does_not_hold_candidate_hostage() -> None:
    plan = _plan()
    pipeline = _Pipeline(plan)
    support = _support(
        pipeline,
        timing=RotationSavedBuildActionTimingEvidence(
            unresolved=("timing ambiguity",),
            unresolved_action_names=("Unused Skill",),
        ),
    )

    result = _run(support, plan)

    assert pipeline.scorecard.candidate_specific_unresolved == ()
    assert pipeline.scorecard.supplied_obligations_satisfied
    assert result.validation.selectable is True


def test_unresolved_range_for_used_action_only_blocks_when_distance_is_relevant() -> None:
    plan = _plan()
    range_evidence = RotationSavedBuildActionRangeEvidence(
        unresolved=("range ambiguity",),
        unresolved_action_names=("Used Skill",),
    )

    no_distance_pipeline = _Pipeline(plan)
    no_distance_result = _run(
        _support(no_distance_pipeline, range_evidence=range_evidence),
        plan,
    )
    assert no_distance_pipeline.scorecard.candidate_specific_unresolved == ()
    assert no_distance_result.validation.selectable is True

    distance_pipeline = _Pipeline(plan)
    distance_result = _run(
        _support(distance_pipeline, range_evidence=range_evidence),
        plan,
        target_distance_windows=(
            RotationTargetDistanceWindow("mechanic", 9.0, 11.0, 20.0),
        ),
    )
    assert distance_pipeline.scorecard.candidate_specific_unresolved == (
        "canonical action range unresolved for used action: Used Skill",
    )
    assert not distance_pipeline.scorecard.supplied_obligations_satisfied
    assert distance_result.validation.selectable is False
