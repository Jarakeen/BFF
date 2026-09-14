from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_runtime_application_pipeline_service import (
    RotationRuntimeApplicationPipelineService,
)
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoice,
    RotationRuntimeExecutableChoiceResolution,
)
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyCandidate,
    RotationRuntimeExecutionStrategyResolution,
)
from services.rotation_runtime_trigger_condition_service import (
    RotationRuntimeActivatedIntent,
    RotationRuntimeTriggerResolution,
)
from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent


def _intent(identity: str, trigger: str) -> RotationRuntimeTriggeredIntent:
    return RotationRuntimeTriggeredIntent(
        intent_id=identity,
        trigger_key=trigger,
        directive="acquire_owned_target",
        source_plan_id="plan",
        source_seat_id="off-tank",
        encounter_id="xalvakka",
        target_key=identity,
        required_capability_type="taunt",
    )


def _activated(identity: str, trigger: str, time_seconds: float) -> RotationRuntimeActivatedIntent:
    return RotationRuntimeActivatedIntent(
        intent=_intent(identity, trigger),
        activated_at_seconds=time_seconds,
        trigger_source="authoritative runtime evidence",
    )


class _TriggerConditions:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve(self, *, intents, observations):
        self.calls.append((tuple(intents), tuple(observations)))
        return self.resolution


class _ExecutionStrategy:
    def __init__(self, *, unresolved_ids=()):
        self.unresolved_ids = set(unresolved_ids)
        self.calls = []

    def resolve(self, *, activated_intent, build):
        self.calls.append((activated_intent, build))
        if activated_intent.intent.intent_id in self.unresolved_ids:
            return RotationRuntimeExecutionStrategyResolution(
                activated_intent=activated_intent,
                unresolved=("canonical capability unresolved",),
            )
        candidate = RotationRuntimeExecutionStrategyCandidate(
            intent_id=activated_intent.intent.intent_id,
            activated_at_seconds=activated_intent.activated_at_seconds,
            directive=activated_intent.intent.directive,
            capability_type="taunt",
            skill_name=f"Taunt {activated_intent.intent.intent_id}",
            bar="front",
            target_key=activated_intent.intent.target_key,
        )
        return RotationRuntimeExecutionStrategyResolution(
            activated_intent=activated_intent,
            candidates=(candidate,),
        )


class _ExecutableChoice:
    def __init__(self, *, unresolved_ids=()):
        self.unresolved_ids = set(unresolved_ids)
        self.plan_action_counts = []

    def resolve(self, *, plan, strategy, **_kwargs):
        self.plan_action_counts.append(len(plan.actions))
        candidate = strategy.candidates[0]
        if candidate.intent_id in self.unresolved_ids:
            return RotationRuntimeExecutableChoiceResolution(
                executable_candidates=(candidate,),
                unresolved=("candidate is not executable now",),
            )
        choice = RotationRuntimeExecutableChoice(
            candidate=candidate,
            active_bar="front",
        )
        return RotationRuntimeExecutableChoiceResolution(
            selected=choice,
            executable_candidates=(candidate,),
        )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Tank Build",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Opening Skill",
                bar="front",
            ),
        ),
    )


def test_pipeline_applies_activated_intents_in_time_order_and_carries_plan_forward() -> None:
    late = _activated("late", "trigger:late", 20.0)
    early = _activated("early", "trigger:early", 10.0)
    trigger = _TriggerConditions(
        RotationRuntimeTriggerResolution(activated=(late, early))
    )
    strategy = _ExecutionStrategy()
    choice = _ExecutableChoice()
    service = RotationRuntimeApplicationPipelineService(
        trigger_conditions=trigger,
        execution_strategy=strategy,
        executable_choice=choice,
    )
    plan = _plan()
    build = PlayerBuild(Name="Rylonia", BuildName="Tank Build")

    result = service.apply(
        plan=plan,
        build=build,
        intents=(early.intent, late.intent),
        observations=(),
        slot_requirements=(),
        target_requirements=(),
        target_windows=(),
        occupancy_requirements=(),
    )

    assert result.initial_plan is plan
    assert result.changed is True
    assert [row.activated_intent.intent.intent_id for row in result.applications] == [
        "early",
        "late",
    ]
    assert choice.plan_action_counts == [1, 2]
    assert [(row.time_seconds, row.name) for row in result.final_plan.actions] == [
        (0.0, "Opening Skill"),
        (10.0, "Taunt early"),
        (20.0, "Taunt late"),
    ]
    assert all(row.applied for row in result.applications)
    assert result.unresolved == ()


def test_strategy_failure_is_preserved_and_does_not_mutate_plan() -> None:
    activated = _activated("blocked", "trigger:blocked", 10.0)
    service = RotationRuntimeApplicationPipelineService(
        trigger_conditions=_TriggerConditions(
            RotationRuntimeTriggerResolution(activated=(activated,))
        ),
        execution_strategy=_ExecutionStrategy(unresolved_ids={"blocked"}),
        executable_choice=_ExecutableChoice(),
    )
    plan = _plan()

    result = service.apply(
        plan=plan,
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
        intents=(activated.intent,),
        observations=(),
        slot_requirements=(),
        target_requirements=(),
        target_windows=(),
        occupancy_requirements=(),
    )

    assert result.final_plan is plan
    assert result.changed is False
    assert result.applications[0].choice is None
    assert result.applications[0].materialization is None
    assert result.unresolved == ("canonical capability unresolved",)


def test_choice_failure_is_preserved_and_does_not_materialize_action() -> None:
    activated = _activated("blocked", "trigger:blocked", 10.0)
    choice = _ExecutableChoice(unresolved_ids={"blocked"})
    service = RotationRuntimeApplicationPipelineService(
        trigger_conditions=_TriggerConditions(
            RotationRuntimeTriggerResolution(activated=(activated,))
        ),
        execution_strategy=_ExecutionStrategy(),
        executable_choice=choice,
    )
    plan = _plan()

    result = service.apply(
        plan=plan,
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
        intents=(activated.intent,),
        observations=(),
        slot_requirements=(),
        target_requirements=(),
        target_windows=(),
        occupancy_requirements=(),
    )

    assert result.final_plan is plan
    assert result.applications[0].choice is not None
    assert result.applications[0].materialization is None
    assert result.unresolved == ("candidate is not executable now",)


def test_pending_intents_and_rejected_observations_remain_visible() -> None:
    pending = _intent("pending", "trigger:pending")
    service = RotationRuntimeApplicationPipelineService(
        trigger_conditions=_TriggerConditions(
            RotationRuntimeTriggerResolution(
                pending=(pending,),
                rejected_observations=("observation is not authoritative",),
            )
        ),
        execution_strategy=_ExecutionStrategy(),
        executable_choice=_ExecutableChoice(),
    )
    plan = _plan()

    result = service.apply(
        plan=plan,
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
        intents=(pending,),
        observations=(),
        slot_requirements=(),
        target_requirements=(),
        target_windows=(),
        occupancy_requirements=(),
    )

    assert result.final_plan is plan
    assert result.trigger_resolution.pending == (pending,)
    assert result.applications == ()
    assert result.unresolved == ("observation is not authoritative",)
