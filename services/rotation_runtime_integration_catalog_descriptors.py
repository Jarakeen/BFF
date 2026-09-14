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
)


__all__ = ["ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS"]
