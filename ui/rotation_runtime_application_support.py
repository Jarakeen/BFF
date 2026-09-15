from __future__ import annotations

"""Apply authoritative runtime observations to the current canonical Rotation plan.

This UI/application boundary does not own runtime mechanics. It gathers the exact
artifacts already owned by canonical Generate, resolves saved-build target identity
through the existing canonical target service, and delegates runtime-triggered action
application to ``RotationRuntimeApplicationPipelineService``.

Live trigger observations and encounter target-state windows remain explicit caller
inputs. The adapter never derives live encounter truth from historical logs, display
labels, encounter names, or Raid Plan prose.
"""

from dataclasses import dataclass
from types import MethodType

from engine.config import get_data_dir
from minmax.rotation_action_target_legality import RotationTargetStateWindow
from minmax.rotation_plan import RotationPlan
from services.rotation_runtime_application_pipeline_service import (
    RotationRuntimeApplicationPipelineResult,
    RotationRuntimeApplicationPipelineService,
)
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoiceService,
)
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyService,
)
from services.rotation_runtime_trigger_condition_service import (
    RotationRuntimeTriggerConditionService,
    RotationRuntimeTriggerObservation,
)
from services.rotation_saved_build_action_target_service import (
    RotationSavedBuildActionTargetEvidence,
    RotationSavedBuildActionTargetService,
)
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityCapabilityService,
)
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


_INSTALLED = False


@dataclass(frozen=True)
class RotationRuntimeApplicationSupportResult:
    pipeline_result: RotationRuntimeApplicationPipelineResult
    target_evidence: RotationSavedBuildActionTargetEvidence

    @property
    def changed(self) -> bool:
        return self.pipeline_result.changed


class RotationRuntimeApplicationSupport:
    """Bridge exact canonical Generate evidence into runtime action application."""

    def __init__(
        self,
        *,
        pipeline: RotationRuntimeApplicationPipelineService | object | None = None,
        target_service: RotationSavedBuildActionTargetService | object | None = None,
    ) -> None:
        if pipeline is None:
            capability_service = SavedBuildUtilityCapabilityService(get_data_dir() / "eso.db")
            pipeline = RotationRuntimeApplicationPipelineService(
                trigger_conditions=RotationRuntimeTriggerConditionService(),
                execution_strategy=RotationRuntimeExecutionStrategyService(capability_service),
                executable_choice=RotationRuntimeExecutableChoiceService(),
            )
        if not callable(getattr(pipeline, "apply", None)):
            raise TypeError("runtime application support requires a pipeline with apply(...)")
        target_service = target_service or RotationSavedBuildActionTargetService()
        if not callable(getattr(target_service, "resolve", None)):
            raise TypeError("runtime application support requires a target service with resolve(...)")
        self.pipeline = pipeline
        self.target_service = target_service

    def install(self, page) -> None:
        page.rotation_runtime_application_support = self
        page.last_rotation_runtime_application_result = None
        page.apply_runtime_trigger_observations = MethodType(
            lambda bound_page, **kwargs: self.apply(bound_page, **kwargs),
            page,
        )

    def apply(
        self,
        page,
        *,
        context: RotationGenerateCanonicalContext,
        observations: tuple[RotationRuntimeTriggerObservation, ...],
        target_windows: tuple[RotationTargetStateWindow, ...],
        initial_bar: str = "front",
    ) -> RotationRuntimeApplicationSupportResult:
        if not isinstance(context, RotationGenerateCanonicalContext):
            raise TypeError("runtime application requires RotationGenerateCanonicalContext")
        if context.effective_build is None:
            raise ValueError(
                "runtime application requires the exact frozen effective-build snapshot from canonical Generate"
            )

        orchestration = getattr(page, "last_canonical_cadence_orchestration_result", None)
        if orchestration is None:
            raise ValueError("runtime application requires a completed canonical Generate result")
        canonical_plan = getattr(orchestration, "final_plan", None)
        if not isinstance(canonical_plan, RotationPlan):
            raise ValueError("canonical Generate result has no final RotationPlan")

        current_plan = getattr(page, "rotation_plan", None)
        if not isinstance(current_plan, RotationPlan):
            current_plan = canonical_plan
        if (
            current_plan.character_name.casefold() != canonical_plan.character_name.casefold()
            or current_plan.build_name.casefold() != canonical_plan.build_name.casefold()
        ):
            raise ValueError(
                "displayed Rotation plan does not belong to the canonical Generate build"
            )

        build = context.player_build_for(None)
        if build is None:
            raise ValueError("runtime application could not materialize the frozen effective build")

        canonical_result = getattr(orchestration, "canonical_result", None)
        candidate_result = getattr(canonical_result, "candidate_result", None)
        if candidate_result is None:
            raise ValueError("canonical Generate result has no candidate evidence")
        slot_evidence = getattr(candidate_result, "action_slot_evidence", None)
        timing_evidence = getattr(candidate_result, "action_timing_evidence", None)
        if slot_evidence is None or timing_evidence is None:
            raise ValueError(
                "canonical Generate result is missing saved-build slot or timing evidence"
            )

        target_evidence = self.target_service.resolve(build)
        intents = tuple(getattr(orchestration, "runtime_triggered_intents", ()) or ())
        pipeline_result = self.pipeline.apply(
            plan=current_plan,
            build=build,
            intents=intents,
            observations=tuple(observations),
            slot_requirements=tuple(getattr(slot_evidence, "slot_requirements", ()) or ()),
            target_requirements=tuple(
                getattr(target_evidence, "target_requirements", ()) or ()
            ),
            target_windows=tuple(target_windows),
            occupancy_requirements=tuple(
                getattr(timing_evidence, "occupancy_requirements", ()) or ()
            ),
            initial_bar=initial_bar,
        )

        result = RotationRuntimeApplicationSupportResult(
            pipeline_result=pipeline_result,
            target_evidence=target_evidence,
        )
        page.last_rotation_runtime_application_result = result
        if pipeline_result.changed:
            setter = getattr(page, "set_rotation_plan", None)
            if not callable(setter):
                raise TypeError("runtime application page must expose set_rotation_plan(plan)")
            setter(pipeline_result.final_plan)
        return result


def install_rotation_runtime_application(page) -> RotationRuntimeApplicationSupport:
    support = RotationRuntimeApplicationSupport()
    support.install(page)
    return support


def install() -> None:
    """Install runtime observation application on every canonical Rotation page."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage

    original_init = CanonicalRotationDashboardPage.__init__

    def init_with_runtime_application(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        install_rotation_runtime_application(self)

    CanonicalRotationDashboardPage.__init__ = init_with_runtime_application
    _INSTALLED = True


__all__ = [
    "RotationRuntimeApplicationSupport",
    "RotationRuntimeApplicationSupportResult",
    "install",
    "install_rotation_runtime_application",
]
