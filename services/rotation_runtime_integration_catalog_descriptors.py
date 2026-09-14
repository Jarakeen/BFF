from __future__ import annotations

"""Catalog metadata for role-neutral Rotation runtime integration boundaries."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.runtime.triggered_intent_projection",
        domain="rotation",
        purpose=(
            "Project already-bound Raid Plan runtime-triggered responsibilities into pending "
            "Rotation execution intent without manufacturing wall-clock timestamps or mutating "
            "the deterministic RotationPlan."
        ),
        implementation_path="services.rotation_runtime_triggered_intent_service",
        inputs=(
            "RaidPlanTriggeredResponsibility",
            "RaidPlanId",
            "RaidPlanSeatId",
        ),
        outputs=("RotationRuntimeTriggeredIntent",),
        responsibilities=("rotation_runtime_triggered_intent_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This service preserves trigger identity, directive, target, capability requirement, "
            "Raid Plan provenance, and encounter identity. It never emits time_seconds and does "
            "not participate in candidate scheduling or cadence optimization."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.runtime.trigger_condition_resolution",
        domain="rotation",
        purpose=(
            "Resolve pending runtime-triggered Rotation intent against authoritative observations "
            "of the exact condition becoming true at an exact runtime clock time."
        ),
        implementation_path="services.rotation_runtime_trigger_condition_service",
        inputs=(
            "RotationRuntimeTriggeredIntent",
            "RotationRuntimeTriggerObservation",
        ),
        outputs=(
            "RotationRuntimeActivatedIntent",
            "RotationRuntimeTriggerResolution",
        ),
        dependencies=("rotation.runtime.triggered_intent_projection",),
        responsibilities=("rotation_runtime_trigger_condition_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only authoritative matching observations may activate intent. Optional encounter, "
            "Raid Plan, and seat scope must match when supplied. Activation records the observed "
            "runtime time but does not choose a skill, bar, action kind, or execution strategy; "
            "therefore it still does not materialize a RotationAction."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.runtime.execution_strategy_resolution",
        domain="rotation",
        purpose=(
            "Resolve one activated runtime intent into exact already-slotted canonical capability "
            "sources that may satisfy the directive, preserving skill, bar, target, and activation provenance."
        ),
        implementation_path="services.rotation_runtime_execution_strategy_service",
        inputs=(
            "RotationRuntimeActivatedIntent",
            "PlayerBuild",
            "SavedBuildUtilityProviderSourceResolution",
        ),
        outputs=(
            "RotationRuntimeExecutionStrategyCandidate",
            "RotationRuntimeExecutionStrategyResolution",
        ),
        dependencies=("rotation.runtime.trigger_condition_resolution",),
        responsibilities=("rotation_runtime_execution_strategy_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reuses canonical saved-build structural utility evidence. Multiple valid slotted providers "
            "remain multiple candidates. The service does not pick a winner, infer a bar swap, interrupt "
            "an occupied action, or emit RotationAction timing/sequence/action-kind state."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.runtime.executable_choice_resolution",
        domain="rotation",
        purpose=(
            "Choose exactly one immediately executable runtime strategy candidate only when the "
            "current active bar and explicit slot, target-state, and occupancy evidence prove it legal."
        ),
        implementation_path="services.rotation_runtime_executable_choice_service",
        inputs=(
            "RotationPlan",
            "RotationRuntimeExecutionStrategyResolution",
            "RotationActionSlotRequirement",
            "RotationActionTargetRequirement",
            "RotationTargetStateWindow",
            "RotationActionOccupancyRequirement",
        ),
        outputs=(
            "RotationRuntimeExecutableChoice",
            "RotationRuntimeExecutableChoiceResolution",
        ),
        dependencies=("rotation.runtime.execution_strategy_resolution",),
        responsibilities=("rotation_runtime_executable_choice_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reuses the canonical RotationActiveBarAssessor plus existing slot, target, and occupancy "
            "legality assessors. Missing evidence fails closed. Inactive-bar candidates require explicit "
            "bar-swap policy, multiple same-bar legal candidates remain ambiguous, and no output is yet a RotationAction."
        ),
    ),
)


__all__ = ["ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS"]
