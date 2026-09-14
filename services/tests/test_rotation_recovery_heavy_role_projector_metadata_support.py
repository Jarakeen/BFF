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
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _seed():
    return RotationPlan(
        character_name="Tank",
        build_name="Role Projector",
        duration_seconds=30.0,
        actions=(),
    )


def _scorecard(_snapshot):
    return SimpleNamespace(active_bar_assessment=None)


def _run(*, explicit_projector=None, role_projector=None):
    bridge = _Bridge()
    workflow = _Workflow()
    pipeline = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )

    def role_resolver(_snapshot):
        return object()

    if role_projector is not None:
        role_resolver.candidate_projector = role_projector

    result = pipeline.run_effects(
        player_build=object(),
        character_build=object(),
        seed_plan=_seed(),
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: object(),
        scorecard_resolver=_scorecard,
        role_aware_input_resolver=role_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        candidate_projector=explicit_projector,
        completion_evidence_factory=lambda _plan: (),
    )
    return result, bridge, workflow


def test_effect_pipeline_uses_role_resolver_projector_when_explicit_projector_is_absent():
    role_projector = object()

    result, bridge, workflow = _run(role_projector=role_projector)

    assert result is workflow.result
    assert bridge.calls[0]["candidate_projector"] is role_projector


def test_effect_pipeline_explicit_projector_overrides_role_resolver_metadata():
    role_projector = object()
    explicit_projector = object()

    _result, bridge, _workflow = _run(
        explicit_projector=explicit_projector,
        role_projector=role_projector,
    )

    assert bridge.calls[0]["candidate_projector"] is explicit_projector
