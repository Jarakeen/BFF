from __future__ import annotations

"""Service-catalog metadata for Rotation Builder gameplay-practice policy."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.gameplay_policy.dd_personal_heal",
        domain="rotation",
        purpose=(
            "Assess organized-endgame DD redundant personal-heal slot practice from "
            "the shared gameplay-policy registry without rewriting ESO mechanics."
        ),
        implementation_path="services.rotation_gameplay_policy_assessment_service",
        inputs=("RotationGameplayPolicyContext", "GameplayPolicy"),
        outputs=("RotationGameplayPolicyAssessment",),
        responsibilities=("rotation_gameplay_policy_assessment",),
        roles=("DPS",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Consumes shared endgame gameplay policy and explicit encounter/assignment "
            "exceptions. It does not infer healing identity from skill names or tooltips."
        ),
    ),
)


__all__ = ["ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS"]
