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
)


__all__ = ["ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS"]
