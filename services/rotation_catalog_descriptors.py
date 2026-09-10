from __future__ import annotations

"""Explicit Rotation Builder service catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit dependency
wiring; the catalog remains a discovery index rather than a service locator.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.healer.canonical_demand_evidence",
        domain="rotation",
        purpose=(
            "Compose canonical healer action, periodic, delayed, special-activation, "
            "and encounter-window services into candidate-specific healing evidence."
        ),
        implementation_path="services.rotation_candidate_healer_role_output_service",
        inputs=(
            "GeneratedRotationCandidate",
            "PlayerBuild",
            "BuildCalculationContext",
            "RotationDemandWindow",
            "RotationHealerReviewedRuntimeObservation",
            "RotationHealerDelayedRuntimeEvidence",
        ),
        outputs=("RotationHealerDemandHealingEvidence",),
        dependencies=("rotation.candidate_generation",),
        responsibilities=("rotation_healer_canonical_demand_evidence",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only: missing first-tick, expiry, refresh, delay, or special "
            "activation facts remain unresolved rather than being inferred."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.role_output",
        domain="rotation",
        purpose=(
            "Convert canonical healer demand-window evidence into comparable modeled "
            "healing per demand-second for role-aware candidate ranking."
        ),
        implementation_path="services.rotation_candidate_healer_role_output_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationDemandWindow",
            "RotationHealerDemandHealingEvidence",
        ),
        outputs=("RotationCandidateRoleOutputEvidence",),
        dependencies=("rotation.healer.canonical_demand_evidence",),
        responsibilities=("rotation_healer_role_output",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Modeled demand-window healing is pre-recipient and pre-overheal; this "
            "service does not claim observed/received HPS or survival."
        ),
    ),
)


__all__ = ["ROTATION_SERVICE_DESCRIPTORS"]
