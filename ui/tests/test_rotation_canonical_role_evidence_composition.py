from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from minmax.skill_component_classification import HealRecipientScope, SkillEffectKind
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import RotationGameplayPolicyStatus
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from ui.rotation_canonical_candidate_support import (
    RotationCanonicalCandidateSupport,
    RotationCanonicalRoleEvidence,
)


class _BuildAdapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _EvidenceService:
    def __init__(self, value):
        self.value = value

    def resolve(self, _build):
        return self.value


class _Pipeline:
    def __init__(self):
        self.calls = []
        self.result = SimpleNamespace(selected_candidate=None)

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Validation:
    def from_candidate_pipeline_result(self, _result):
        return SimpleNamespace(scope="candidate_family", selectable=True, reasons=())


class _ActiveBarAssessor:
    def __init__(self):
        self.result = SimpleNamespace(violations=())

    def assess(self, _plan, *, initial_bar="front"):
        return self.result


class _Coefficients:
    def resolve_name(self, _name):
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=77),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, _skill_rank_id):
        return (
            SimpleNamespace(
                effect_kind=SkillEffectKind.HEAL,
                heal_recipient_scope=HealRecipientScope.SELF,
            ),
        )


class _TooltipService:
    def __init__(self):
        self.coefficients = _Coefficients()
        self.components = _Components()


class _PlanEvidenceProvider:
    def evaluate_plan(self, candidate):
        return SimpleNamespace(
            role_output_value=165_000.0,
            assigned_support_value=0.0,
            primary_role_displacement_seconds=0.0,
            role_hard_obligation_satisfied=True,
            role_hard_obligation_reasons=(),
        )


def _scorecard() -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _support(pipeline: _Pipeline) -> RotationCanonicalCandidateSupport:
    from services.rotation_saved_build_action_range_service import (
        RotationSavedBuildActionRangeEvidence,
    )
    from services.rotation_saved_build_action_slot_service import (
        RotationSavedBuildActionSlotEvidence,
    )
    from services.rotation_saved_build_action_timing_service import (
        RotationSavedBuildActionTimingEvidence,
    )

    return RotationCanonicalCandidateSupport(
        build_adapter=_BuildAdapter(),
        pipeline=pipeline,
        validation_support=_Validation(),
        action_timing_service=_EvidenceService(RotationSavedBuildActionTimingEvidence()),
        action_range_service=_EvidenceService(RotationSavedBuildActionRangeEvidence()),
        action_slot_service=_EvidenceService(RotationSavedBuildActionSlotEvidence()),
        active_bar_assessor=_ActiveBarAssessor(),
        skill_tooltip_service=_TooltipService(),
    )


def _run(service, *, role_evidence=None):
    player_build = SimpleNamespace(
        Role="DD",
        FrontBarSkills=("Personal Heal",),
        BackBarSkills=(),
    )
    plan = RotationPlan(
        character_name="Test",
        build_name="DD",
        duration_seconds=30.0,
        actions=(),
    )
    return service.run_effects(
        player_build=player_build,
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: object(),
        scorecard_resolver=lambda _snapshot: _scorecard(),
        resource=object(),
        maximum_amount=30_000,
        trigger_fraction=0.30,
        role_evidence=role_evidence,
    )


def test_canonical_ui_composes_final_dd_role_and_gameplay_policy_evidence() -> None:
    pipeline = _Pipeline()
    service = _support(pipeline)
    role_evidence = RotationCanonicalRoleEvidence(
        plan_evidence_provider=_PlanEvidenceProvider(),
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        content_type="trial",
        reliable_group_healing=True,
    )

    result = _run(service, role_evidence=role_evidence)

    assert result.pipeline_result is pipeline.result
    resolver = pipeline.calls[0]["role_aware_input_resolver"]
    assert resolver is not None

    snapshot = SimpleNamespace(
        candidate_id="baseline",
        plan=pipeline.calls[0]["seed_plan"],
        replay=SimpleNamespace(
            final_projection=SimpleNamespace(
                run=SimpleNamespace(
                    sustain=SimpleNamespace(minimum_amount=4_321),
                )
            )
        ),
    )
    role_input = resolver(snapshot)

    assert role_input.role_key == "dd"
    assert role_input.role_output_value == pytest.approx(165_000.0)
    assert role_input.sustain_margin == pytest.approx(4_321.0)
    assert role_input.gameplay_policy_assessment is not None
    assert (
        role_input.gameplay_policy_assessment.status
        is RotationGameplayPolicyStatus.DISFAVORED
    )
    assert role_input.scorecard.active_bar_assessment is not None


def test_canonical_ui_preserves_legacy_effect_path_without_role_evidence() -> None:
    pipeline = _Pipeline()
    service = _support(pipeline)

    _run(service)

    assert pipeline.calls[0]["role_aware_input_resolver"] is None


def test_dd_role_evidence_requires_explicit_content_type() -> None:
    pipeline = _Pipeline()
    service = _support(pipeline)
    evidence = RotationCanonicalRoleEvidence(
        plan_evidence_provider=_PlanEvidenceProvider(),
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        reliable_group_healing=True,
    )

    with pytest.raises(ValueError, match="content_type"):
        _run(service, role_evidence=evidence)
