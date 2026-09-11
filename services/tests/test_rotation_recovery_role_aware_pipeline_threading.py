from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)
from services.rotation_role_aware_ranking_service import RotationRoleAwareRankingInput


class _WorkflowFinalFamily:
    def __init__(self) -> None:
        self.effect_calls = []
        self.role_calls = []
        self.effect_callback = lambda snapshots: ("effects", snapshots)
        self.role_callback = lambda snapshots: ("effects-role", snapshots)

    def effect_evaluator(self, **kwargs):
        self.effect_calls.append(kwargs)
        return self.effect_callback

    def effect_role_aware_evaluator(self, **kwargs):
        self.role_calls.append(kwargs)
        return self.role_callback


class _WorkflowOrchestration:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def orchestrate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_workflow_selects_effect_role_aware_final_evaluator_when_role_evidence_exists() -> None:
    final_family = _WorkflowFinalFamily()
    orchestration = _WorkflowOrchestration()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        final_family_service=final_family,
        orchestration_service=orchestration,
    )
    role_resolver = lambda snapshot: snapshot
    scorecard_resolver = lambda snapshot: snapshot
    character_build = object()

    result = service.run_effects(
        player_build=object(),
        character_build=character_build,
        candidates=(object(),),
        scorecard_resolver=scorecard_resolver,
        role_aware_input_resolver=role_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: heavy,
    )

    assert result is orchestration.result
    assert final_family.effect_calls == []
    assert len(final_family.role_calls) == 1
    role_call = final_family.role_calls[0]
    assert role_call["build"] is character_build
    assert role_call["input_resolver"] is role_resolver
    assert orchestration.calls[0]["evaluate_final_family"] is final_family.role_callback


class _GenerationBridge:
    def __init__(self) -> None:
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(candidates=(object(),))


class _PipelineWorkflow:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CanonicalScorecardPipeline(RotationRecoveryHeavyCandidatePipelineService):
    def __init__(self, *, canonical_scorecard, **kwargs) -> None:
        super().__init__(**kwargs)
        self.canonical_scorecard = canonical_scorecard

    def _with_saved_build_bar_access(self, player_build, resolver):
        return lambda snapshot: self.canonical_scorecard


def test_pipeline_replaces_role_input_scorecard_with_final_canonical_scorecard() -> None:
    bridge = _GenerationBridge()
    workflow = _PipelineWorkflow()
    canonical_scorecard = object()
    stale_scorecard = object()
    service = _CanonicalScorecardPipeline(
        canonical_scorecard=canonical_scorecard,
        generation_bridge=bridge,
        workflow=workflow,
    )
    role_input = RotationRoleAwareRankingInput(
        candidate_id="candidate",
        scorecard=stale_scorecard,
        role_key="dd",
        role_output_value=100000.0,
        role_output_label="effective damage",
        assigned_support_value=0.0,
        assigned_support_label="assigned support coverage",
        sustain_margin=5000.0,
        primary_role_displacement_seconds=0.0,
    )
    role_resolver = lambda snapshot: role_input

    result = service.run_effects(
        player_build=object(),
        character_build=object(),
        seed_plan=object(),
        priorities=object(),
        evaluator_resolver=lambda candidate_id: None,
        scorecard_resolver=lambda snapshot: stale_scorecard,
        role_aware_input_resolver=role_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: heavy,
    )

    assert result is workflow.result
    assert len(workflow.calls) == 1
    call = workflow.calls[0]
    assert call["role_aware_input_resolver"] is not role_resolver
    snapshot = SimpleNamespace(candidate_id="candidate", plan=object())
    resolved = call["role_aware_input_resolver"](snapshot)
    assert resolved.scorecard is canonical_scorecard
    assert role_input.scorecard is stale_scorecard
