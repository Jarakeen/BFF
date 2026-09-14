from __future__ import annotations

"""Compose the canonical runtime-triggered Rotation execution boundaries.

This service is orchestration only. Trigger truth, capability evidence, executable-choice
legality, and action insertion remain owned by their dedicated services. The pipeline
processes activated intents in deterministic activation order and carries each successful
immutable plan forward so later runtime intents see the plan actually produced so far.
"""

from dataclasses import dataclass

from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_runtime_action_materialization_service import (
    RotationRuntimeActionMaterialization,
    RotationRuntimeActionMaterializationService,
)
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoiceResolution,
    RotationRuntimeExecutableChoiceService,
)
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyResolution,
    RotationRuntimeExecutionStrategyService,
)
from services.rotation_runtime_trigger_condition_service import (
    RotationRuntimeActivatedIntent,
    RotationRuntimeTriggerConditionService,
    RotationRuntimeTriggerObservation,
    RotationRuntimeTriggerResolution,
)
from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent


@dataclass(frozen=True)
class RotationRuntimeIntentApplication:
    activated_intent: RotationRuntimeActivatedIntent
    strategy: RotationRuntimeExecutionStrategyResolution
    choice: RotationRuntimeExecutableChoiceResolution | None = None
    materialization: RotationRuntimeActionMaterialization | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def applied(self) -> bool:
        return self.materialization is not None and self.choice is not None and self.choice.resolved


@dataclass(frozen=True)
class RotationRuntimeApplicationPipelineResult:
    initial_plan: RotationPlan
    final_plan: RotationPlan
    trigger_resolution: RotationRuntimeTriggerResolution
    applications: tuple[RotationRuntimeIntentApplication, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.final_plan != self.initial_plan


class RotationRuntimeApplicationPipelineService:
    """Run canonical runtime-triggered intent through existing execution boundaries."""

    def __init__(
        self,
        *,
        trigger_conditions: RotationRuntimeTriggerConditionService | object,
        execution_strategy: RotationRuntimeExecutionStrategyService | object,
        executable_choice: RotationRuntimeExecutableChoiceService | object,
        materializer: RotationRuntimeActionMaterializationService | object | None = None,
    ) -> None:
        for dependency, method, label in (
            (trigger_conditions, "resolve", "trigger condition resolver"),
            (execution_strategy, "resolve", "execution strategy resolver"),
            (executable_choice, "resolve", "executable choice resolver"),
        ):
            if not callable(getattr(dependency, method, None)):
                raise TypeError(f"runtime application pipeline requires {label}")
        self.trigger_conditions = trigger_conditions
        self.execution_strategy = execution_strategy
        self.executable_choice = executable_choice
        self.materializer = materializer or RotationRuntimeActionMaterializationService()
        if not callable(getattr(self.materializer, "materialize", None)):
            raise TypeError("runtime application pipeline requires action materializer")

    def apply(
        self,
        *,
        plan: RotationPlan,
        build: PlayerBuild,
        intents: tuple[RotationRuntimeTriggeredIntent, ...],
        observations: tuple[RotationRuntimeTriggerObservation, ...],
        slot_requirements: tuple[RotationActionSlotRequirement, ...],
        target_requirements: tuple[RotationActionTargetRequirement, ...],
        target_windows: tuple[RotationTargetStateWindow, ...],
        occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...],
        initial_bar: str = "front",
    ) -> RotationRuntimeApplicationPipelineResult:
        if not isinstance(plan, RotationPlan):
            raise TypeError("runtime application pipeline requires RotationPlan")
        if not isinstance(build, PlayerBuild):
            raise TypeError("runtime application pipeline requires PlayerBuild")

        trigger_resolution = self.trigger_conditions.resolve(
            intents=tuple(intents),
            observations=tuple(observations),
        )
        working_plan = plan
        applications: list[RotationRuntimeIntentApplication] = []
        unresolved: list[str] = list(trigger_resolution.rejected_observations)

        activated = tuple(
            sorted(
                trigger_resolution.activated,
                key=lambda row: (
                    float(row.activated_at_seconds),
                    row.intent.intent_id.casefold(),
                ),
            )
        )
        for activated_intent in activated:
            strategy = self.execution_strategy.resolve(
                activated_intent=activated_intent,
                build=build,
            )
            if strategy.unresolved or not strategy.candidates:
                reasons = tuple(strategy.unresolved) or (
                    "runtime execution strategy produced no candidates",
                )
                unresolved.extend(reasons)
                applications.append(
                    RotationRuntimeIntentApplication(
                        activated_intent=activated_intent,
                        strategy=strategy,
                        unresolved=reasons,
                    )
                )
                continue

            choice = self.executable_choice.resolve(
                plan=working_plan,
                strategy=strategy,
                slot_requirements=tuple(slot_requirements),
                target_requirements=tuple(target_requirements),
                target_windows=tuple(target_windows),
                occupancy_requirements=tuple(occupancy_requirements),
                initial_bar=initial_bar,
            )
            if not choice.resolved or choice.selected is None:
                reasons = tuple(choice.unresolved) or (
                    "runtime execution choice did not resolve exactly one executable candidate",
                )
                unresolved.extend(reasons)
                applications.append(
                    RotationRuntimeIntentApplication(
                        activated_intent=activated_intent,
                        strategy=strategy,
                        choice=choice,
                        unresolved=reasons,
                    )
                )
                continue

            materialization = self.materializer.materialize(
                plan=working_plan,
                choice=choice.selected,
            )
            working_plan = materialization.plan
            applications.append(
                RotationRuntimeIntentApplication(
                    activated_intent=activated_intent,
                    strategy=strategy,
                    choice=choice,
                    materialization=materialization,
                )
            )

        return RotationRuntimeApplicationPipelineResult(
            initial_plan=plan,
            final_plan=working_plan,
            trigger_resolution=trigger_resolution,
            applications=tuple(applications),
            unresolved=tuple(dict.fromkeys(str(value).strip() for value in unresolved if str(value).strip())),
        )


__all__ = [
    "RotationRuntimeApplicationPipelineResult",
    "RotationRuntimeApplicationPipelineService",
    "RotationRuntimeIntentApplication",
]
