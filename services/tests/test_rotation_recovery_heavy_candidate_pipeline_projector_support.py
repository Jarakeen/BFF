from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)


class _Bridge:
    def __init__(self):
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(candidates=(object(),))


class _Workflow:
    def __init__(self):
        self.generic_calls = []
        self.effect_calls = []
        self.result = object()

    def run_generic(self, **kwargs):
        self.generic_calls.append(kwargs)
        return self.result

    def run_effects(self, **kwargs):
        self.effect_calls.append(kwargs)
        return self.result


def _seed():
    return RotationPlan(
        character_name="Tank",
        build_name="Projection Test",
        duration_seconds=30.0,
        actions=(),
    )


def _scorecard(_snapshot):
    return SimpleNamespace(active_bar_assessment=None)


def test_generic_pipeline_forwards_candidate_projector_to_generation_bridge():
    bridge = _Bridge()
    workflow = _Workflow()
    pipeline = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )
    projector = object()

    result = pipeline.run_generic(
        player_build=object(),
        seed_plan=_seed(),
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        candidate_projector=projector,
    )

    assert result is workflow.result
    assert bridge.calls[0]["candidate_projector"] is projector
    assert workflow.generic_calls[0]["candidates"] == (bridge.build(**bridge.calls[0]).candidates[0],)


def test_effect_pipeline_forwards_candidate_projector_to_generation_bridge():
    bridge = _Bridge()
    workflow = _Workflow()
    pipeline = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )
    projector = object()

    result = pipeline.run_effects(
        player_build=object(),
        character_build=object(),
        seed_plan=_seed(),
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        candidate_projector=projector,
        completion_evidence_factory=lambda _plan: (),
    )

    assert result is workflow.result
    assert bridge.calls[0]["candidate_projector"] is projector
    assert len(workflow.effect_calls) == 1
