from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RotationRecoveryHeavyCandidateOrchestrationService,
)
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)
from services.rotation_recovery_heavy_candidate_stabilization_service import (
    RotationRecoveryHeavyCandidateStabilizationService,
)
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(),
    )


def _factory(plan):
    return lambda _heavy: None


class _CaptureStabilizer:
    def __init__(self):
        self.calls = []

    def stabilize(self, **kwargs):
        self.calls.append(kwargs)
        return "stabilized"


class _CaptureCandidateStabilizer:
    def __init__(self):
        self.calls = []

    def stabilize(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(plan=_plan(), replay="replay")


class _Selection:
    def rank(self, _joined):
        return ()


class _CaptureOrchestration:
    def __init__(self):
        self.calls = []

    def orchestrate(self, **kwargs):
        self.calls.append(kwargs)
        return "orchestrated"


class _FinalFamily:
    @staticmethod
    def generic_evaluator(**_kwargs):
        return lambda _snapshots: ()

    @staticmethod
    def effect_evaluator(**_kwargs):
        return lambda _snapshots: ()


class _Bridge:
    def build(self, **_kwargs):
        return SimpleNamespace(candidates=("candidate",))


class _CaptureWorkflow:
    def __init__(self):
        self.calls = []

    def run_generic(self, **kwargs):
        self.calls.append(kwargs)
        return "pipeline-result"


def test_candidate_stabilization_threads_plan_aware_restore_factory() -> None:
    downstream = _CaptureStabilizer()
    service = RotationRecoveryHeavyCandidateStabilizationService(
        stabilization_service=downstream,
    )

    result = service.stabilize(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        generate=lambda _pressure: _plan(),
        evaluate_candidate=lambda _plan, _replay: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver_factory=_factory,
    )

    assert result == "stabilized"
    assert downstream.calls[0]["restoration_resolver"] is None
    assert downstream.calls[0]["restoration_resolver_factory"] is _factory


def test_orchestration_threads_plan_aware_restore_factory_to_each_candidate() -> None:
    downstream = _CaptureCandidateStabilizer()
    service = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=downstream,
        selection_service=_Selection(),
    )
    candidate = RecoveryHeavyCandidateOrchestrationInput(
        candidate_id="candidate",
        generate=lambda _pressure: _plan(),
        evaluate_candidate=lambda _plan, _replay: SimpleNamespace(candidate_id="candidate"),
    )

    result = service.orchestrate(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        candidates=(candidate,),
        evaluate_final_family=lambda _snapshots: (
            SimpleNamespace(candidate_id="candidate"),
        ),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver_factory=_factory,
    )

    assert len(result.stabilized_candidates) == 1
    assert downstream.calls[0]["restoration_resolver"] is None
    assert downstream.calls[0]["restoration_resolver_factory"] is _factory


def test_workflow_threads_plan_aware_restore_factory_to_orchestration() -> None:
    orchestration = _CaptureOrchestration()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestration,
        final_family_service=_FinalFamily(),
    )

    result = service.run_generic(
        player_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        candidates=(),
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver_factory=_factory,
    )

    assert result == "orchestrated"
    assert orchestration.calls[0]["restoration_resolver"] is None
    assert orchestration.calls[0]["restoration_resolver_factory"] is _factory


def test_pipeline_threads_plan_aware_restore_factory_to_workflow() -> None:
    workflow = _CaptureWorkflow()
    service = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=_Bridge(),
        workflow=workflow,
    )

    result = service.run_generic(
        player_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        seed_plan=_plan(),
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: None,
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver_factory=_factory,
    )

    assert result == "pipeline-result"
    assert workflow.calls[0]["restoration_resolver"] is None
    assert workflow.calls[0]["restoration_resolver_factory"] is _factory
