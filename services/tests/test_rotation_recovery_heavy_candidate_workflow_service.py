from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)


class _FakeFinalFamilyService:
    def __init__(self) -> None:
        self.generic_calls = []
        self.effect_calls = []
        self.generic_callback = lambda snapshots: ("generic", snapshots)
        self.effect_callback = lambda snapshots: ("effects", snapshots)

    def generic_evaluator(self, *, scorecard_resolver):
        self.generic_calls.append({"scorecard_resolver": scorecard_resolver})
        return self.generic_callback

    def effect_evaluator(
        self,
        *,
        build,
        scorecard_resolver,
        requirements=(),
        passives=(),
    ):
        self.effect_calls.append(
            {
                "build": build,
                "scorecard_resolver": scorecard_resolver,
                "requirements": requirements,
                "passives": passives,
            }
        )
        return self.effect_callback


class _FakeOrchestrationService:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(selected_candidate="selected")

    def orchestrate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_workflow_composes_generic_final_family_evaluator() -> None:
    orchestration = _FakeOrchestrationService()
    final_family = _FakeFinalFamilyService()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestration,
        final_family_service=final_family,
    )
    player_build = object()
    candidates = (object(), object())
    scorecard_resolver = lambda snapshot: snapshot
    restoration_resolver = lambda heavy: heavy
    reserve_resolver = lambda plan, replay: ()
    calculation_context = object()
    maximum_event_resolver = object()
    displayed_recovery_factory = object()
    runtime_state_factory = object()

    result = service.run_generic(
        player_build=player_build,
        candidates=candidates,
        scorecard_resolver=scorecard_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=restoration_resolver,
        reserve_assessment_resolver=reserve_resolver,
        max_iterations=8,
        calculation_context=calculation_context,
        maximum_event_resolver=maximum_event_resolver,
        displayed_recovery_resolver_factory=displayed_recovery_factory,
        runtime_combat_state_resolver_factory=runtime_state_factory,
    )

    assert result is orchestration.result
    assert final_family.generic_calls == [
        {"scorecard_resolver": scorecard_resolver}
    ]
    assert len(orchestration.calls) == 1
    call = orchestration.calls[0]
    assert call["build"] is player_build
    assert call["candidates"] == candidates
    assert call["evaluate_final_family"] is final_family.generic_callback
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 30000
    assert call["trigger_fraction"] == 0.30
    assert call["restoration_resolver"] is restoration_resolver
    assert call["reserve_assessment_resolver"] is reserve_resolver
    assert call["max_iterations"] == 8
    assert call["calculation_context"] is calculation_context
    assert call["maximum_event_resolver"] is maximum_event_resolver
    assert call["displayed_recovery_resolver_factory"] is displayed_recovery_factory
    assert call["runtime_combat_state_resolver_factory"] is runtime_state_factory


def test_workflow_keeps_player_and_character_build_boundaries_explicit() -> None:
    orchestration = _FakeOrchestrationService()
    final_family = _FakeFinalFamilyService()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestration,
        final_family_service=final_family,
    )
    player_build = object()
    character_build = object()
    scorecard_resolver = lambda snapshot: snapshot
    requirement = object()
    passive_a = object()
    passive_b = object()
    displayed_recovery_factory = object()
    runtime_state_factory = object()

    result = service.run_effects(
        player_build=player_build,
        character_build=character_build,
        candidates=(object(),),
        scorecard_resolver=scorecard_resolver,
        requirements=(requirement,),
        passives=(passive_a, passive_b),
        resource=ResourceType.STAMINA,
        maximum_amount=25000,
        trigger_fraction=0.25,
        restoration_resolver=lambda heavy: heavy,
        displayed_recovery_resolver_factory=displayed_recovery_factory,
        runtime_combat_state_resolver_factory=runtime_state_factory,
    )

    assert result is orchestration.result
    assert len(final_family.effect_calls) == 1
    effect_call = final_family.effect_calls[0]
    assert effect_call["build"] is character_build
    assert effect_call["build"] is not player_build
    assert effect_call["scorecard_resolver"] is scorecard_resolver
    assert effect_call["requirements"] == (requirement,)
    assert effect_call["passives"] == (passive_a, passive_b)

    assert len(orchestration.calls) == 1
    orchestration_call = orchestration.calls[0]
    assert orchestration_call["build"] is player_build
    assert orchestration_call["build"] is not character_build
    assert orchestration_call["evaluate_final_family"] is final_family.effect_callback
    assert orchestration_call["resource"] is ResourceType.STAMINA
    assert orchestration_call["displayed_recovery_resolver_factory"] is displayed_recovery_factory
    assert orchestration_call["runtime_combat_state_resolver_factory"] is runtime_state_factory


def test_workflow_materializes_effect_evidence_before_callback_capture() -> None:
    orchestration = _FakeOrchestrationService()
    final_family = _FakeFinalFamilyService()
    service = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestration,
        final_family_service=final_family,
    )
    requirement_a = object()
    requirement_b = object()
    passive_a = object()
    passive_b = object()

    service.run_effects(
        player_build=object(),
        character_build=object(),
        candidates=(),
        scorecard_resolver=lambda snapshot: snapshot,
        requirements=iter((requirement_a, requirement_b)),
        passives=iter((passive_a, passive_b)),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: heavy,
    )

    effect_call = final_family.effect_calls[0]
    assert effect_call["requirements"] == (requirement_a, requirement_b)
    assert effect_call["passives"] == (passive_a, passive_b)
    assert orchestration.calls[0]["displayed_recovery_resolver_factory"] is None
    assert orchestration.calls[0]["runtime_combat_state_resolver_factory"] is None
