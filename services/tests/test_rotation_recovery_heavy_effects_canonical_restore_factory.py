from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)


def _plan(name: str = "DF Healer") -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=30.0,
        actions=(),
    )


class _Bridge:
    def build(self, **_kwargs):
        return SimpleNamespace(candidates=("candidate",))


class _Workflow:
    def __init__(self) -> None:
        self.calls = []

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return "result"


class _HeavySustain:
    def __init__(self) -> None:
        self.calls = []
        self.resolver = lambda _heavy: None

    def restoration_resolver_for_plan(self, **kwargs):
        self.calls.append(kwargs)
        return self.resolver


def _service():
    workflow = _Workflow()
    heavy = _HeavySustain()
    return (
        RotationRecoveryHeavyCandidatePipelineService(
            generation_bridge=_Bridge(),
            workflow=workflow,
            heavy_sustain_service=heavy,
        ),
        workflow,
        heavy,
    )


def _run(service, **kwargs):
    return service.run_effects(
        player_build=kwargs.pop("player_build", PlayerBuild(Name="Magrat", BuildName="DF Healer")),
        character_build=kwargs.pop("character_build", object()),
        seed_plan=kwargs.pop("seed_plan", _plan()),
        priorities=object(),
        evaluator_resolver=lambda _candidate_id: None,
        scorecard_resolver=lambda _snapshot: None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        **kwargs,
    )


def test_effects_pipeline_builds_canonical_restore_factory_from_completion_evidence() -> None:
    service, workflow, heavy = _service()
    player_build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    character_build = object()
    evidence_calls = []
    evidence = object()

    def completion_evidence_factory(plan):
        evidence_calls.append(plan)
        return (evidence,)

    result = _run(
        service,
        player_build=player_build,
        character_build=character_build,
        completion_evidence_factory=completion_evidence_factory,
        initial_bar="back",
    )

    assert result == "result"
    assert workflow.calls[0]["restoration_resolver"] is None
    factory = workflow.calls[0]["restoration_resolver_factory"]
    assert callable(factory)
    assert evidence_calls == []

    generated_plan = _plan("regenerated")
    resolver = factory(generated_plan)

    assert resolver is heavy.resolver
    assert evidence_calls == [generated_plan]
    assert len(heavy.calls) == 1
    assert heavy.calls[0]["character_build"] is character_build
    assert heavy.calls[0]["sustain_build"] is player_build
    assert heavy.calls[0]["plan"] is generated_plan
    assert heavy.calls[0]["resource"] is ResourceType.MAGICKA
    assert heavy.calls[0]["initial_bar"] == "back"
    assert heavy.calls[0]["completion_evidence"] == (evidence,)


def test_completion_evidence_factory_cannot_double_source_restoration() -> None:
    service, _workflow, _heavy = _service()

    with pytest.raises(ValueError, match="cannot be combined"):
        _run(
            service,
            completion_evidence_factory=lambda _plan: (),
            restoration_resolver=lambda _heavy: None,
        )

    with pytest.raises(ValueError, match="cannot be combined"):
        _run(
            service,
            completion_evidence_factory=lambda _plan: (),
            restoration_resolver_factory=lambda _plan: (lambda _heavy: None),
        )


def test_explicit_legacy_restore_source_remains_untouched_without_completion_factory() -> None:
    service, workflow, heavy = _service()
    explicit = lambda _heavy: None

    result = _run(service, restoration_resolver=explicit)

    assert result == "result"
    assert workflow.calls[0]["restoration_resolver"] is explicit
    assert workflow.calls[0]["restoration_resolver_factory"] is None
    assert heavy.calls == []
