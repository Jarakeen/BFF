from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)


class _Bridge:
    def __init__(self) -> None:
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(candidates=("baseline-candidate", "option-candidate"))


class _Workflow:
    def __init__(self) -> None:
        self.generic_calls = []
        self.effect_calls = []

    def run_generic(self, **kwargs):
        self.generic_calls.append(kwargs)
        return "generic-result"

    def run_effects(self, **kwargs):
        self.effect_calls.append(kwargs)
        return "effect-result"


def test_generic_pipeline_bridges_generation_into_recovery_workflow() -> None:
    bridge = _Bridge()
    workflow = _Workflow()
    service = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )

    player_build = object()
    seed_plan = object()
    priorities = object()
    evaluator_resolver = object()
    scorecard_resolver = object()
    restoration_resolver = object()
    reserve_resolver = object()
    wait_factory = object()
    calculation_context = object()
    maximum_event_resolver = object()
    displayed_recovery_factory = object()
    runtime_state_factory = object()
    demands = (item for item in ("demand-a", "demand-b"))
    options = (item for item in ("option-a", "option-b"))

    result = service.run_generic(
        player_build=player_build,
        seed_plan=seed_plan,
        priorities=priorities,
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=scorecard_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        restoration_resolver=restoration_resolver,
        demands=demands,
        options=options,
        wait_decision_factory=wait_factory,
        reserve_assessment_resolver=reserve_resolver,
        max_iterations=8,
        baseline_id="saved-build-baseline",
        calculation_context=calculation_context,
        maximum_event_resolver=maximum_event_resolver,
        displayed_recovery_resolver_factory=displayed_recovery_factory,
        runtime_combat_state_resolver_factory=runtime_state_factory,
    )

    assert result == "generic-result"
    assert bridge.calls == [
        {
            "seed_plan": seed_plan,
            "priorities": priorities,
            "evaluator_resolver": evaluator_resolver,
            "demands": ("demand-a", "demand-b"),
            "options": ("option-a", "option-b"),
            "wait_decision_factory": wait_factory,
            "baseline_id": "saved-build-baseline",
        }
    ]
    assert workflow.generic_calls == [
        {
            "player_build": player_build,
            "candidates": ("baseline-candidate", "option-candidate"),
            "scorecard_resolver": scorecard_resolver,
            "resource": ResourceType.MAGICKA,
            "maximum_amount": 30000,
            "trigger_fraction": 0.35,
            "restoration_resolver": restoration_resolver,
            "reserve_assessment_resolver": reserve_resolver,
            "max_iterations": 8,
            "calculation_context": calculation_context,
            "maximum_event_resolver": maximum_event_resolver,
            "displayed_recovery_resolver_factory": displayed_recovery_factory,
            "runtime_combat_state_resolver_factory": runtime_state_factory,
        }
    ]


def test_effect_pipeline_preserves_build_boundary_and_materializes_effect_evidence() -> None:
    bridge = _Bridge()
    workflow = _Workflow()
    service = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )

    player_build = object()
    character_build = object()
    seed_plan = object()
    priorities = object()
    evaluator_resolver = object()
    scorecard_resolver = object()
    restoration_resolver = object()
    calculation_context = object()
    maximum_event_resolver = object()
    displayed_recovery_factory = object()
    runtime_state_factory = object()
    requirements = (item for item in ("major-brittle", "minor-vulnerability"))
    passives = (item for item in ("class-passive", "armor-passive"))

    result = service.run_effects(
        player_build=player_build,
        character_build=character_build,
        seed_plan=seed_plan,
        priorities=priorities,
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=scorecard_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.4,
        restoration_resolver=restoration_resolver,
        demands=("support-window",),
        options=("refresh-option",),
        requirements=requirements,
        passives=passives,
        calculation_context=calculation_context,
        maximum_event_resolver=maximum_event_resolver,
        displayed_recovery_resolver_factory=displayed_recovery_factory,
        runtime_combat_state_resolver_factory=runtime_state_factory,
    )

    assert result == "effect-result"
    assert bridge.calls[0]["demands"] == ("support-window",)
    assert bridge.calls[0]["options"] == ("refresh-option",)
    assert workflow.effect_calls == [
        {
            "player_build": player_build,
            "character_build": character_build,
            "candidates": ("baseline-candidate", "option-candidate"),
            "scorecard_resolver": scorecard_resolver,
            "requirements": ("major-brittle", "minor-vulnerability"),
            "passives": ("class-passive", "armor-passive"),
            "resource": ResourceType.MAGICKA,
            "maximum_amount": 32000,
            "trigger_fraction": 0.4,
            "restoration_resolver": restoration_resolver,
            "reserve_assessment_resolver": None,
            "max_iterations": 6,
            "calculation_context": calculation_context,
            "maximum_event_resolver": maximum_event_resolver,
            "displayed_recovery_resolver_factory": displayed_recovery_factory,
            "runtime_combat_state_resolver_factory": runtime_state_factory,
        }
    ]
    assert workflow.effect_calls[0]["player_build"] is player_build
    assert workflow.effect_calls[0]["character_build"] is character_build
