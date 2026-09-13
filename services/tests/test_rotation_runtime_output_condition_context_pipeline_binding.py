from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)


class _GenerationBridge:
    def build(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(candidates=())


class _Workflow:
    def run_generic(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(marker="pipeline")


class _FinalFamily:
    def generic_evaluator(self, **kwargs):
        self.kwargs = kwargs
        return object()


class _Orchestrator:
    def orchestrate(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(marker="workflow")


def _plan():
    return RotationPlan(
        character_name="Runtime Context",
        build_name="DD",
        duration_seconds=10.0,
        actions=(),
    )


def _factory(plan):
    del plan
    return lambda _event: frozenset({"reviewed_runtime_condition"})


def test_pipeline_forwards_output_condition_context_factory_to_workflow() -> None:
    bridge = _GenerationBridge()
    workflow = _Workflow()
    service = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )

    result = service.run_generic(
        player_build=PlayerBuild(Name="Runtime Context", BuildName="DD"),
        seed_plan=_plan(),
        priorities=SimpleNamespace(),
        evaluator_resolver=lambda *_args, **_kwargs: None,
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        runtime_output_condition_context_resolver_factory=_factory,
    )

    assert result.marker == "pipeline"
    assert (
        workflow.kwargs["runtime_output_condition_context_resolver_factory"]
        is _factory
    )


def test_workflow_forwards_output_condition_context_factory_to_orchestrator() -> None:
    orchestrator = _Orchestrator()
    final_family = _FinalFamily()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestrator,
        final_family_service=final_family,
    )

    result = service.run_generic(
        player_build=PlayerBuild(Name="Runtime Context", BuildName="DD"),
        candidates=(),
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        runtime_output_condition_context_resolver_factory=_factory,
    )

    assert result.marker == "workflow"
    assert (
        orchestrator.kwargs["runtime_output_condition_context_resolver_factory"]
        is _factory
    )
