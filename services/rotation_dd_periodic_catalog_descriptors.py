from __future__ import annotations

"""DD periodic runtime semantics catalog metadata for Rotation Builder."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.dd.periodic_runtime_semantics_gap_audit",
        domain="rotation",
        purpose=(
            "Audit selected saved-build DD skills for verified periodic damage components "
            "that still lack reviewed runtime semantics."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_runtime_semantics_gap_audit_service"
        ),
        inputs=(
            "PlayerBuild",
            "CanonicalSkillIdentity",
            "SkillComponentClassification",
            "RotationPeriodicDamageRuntimeSemantics",
        ),
        outputs=("RotationDDPeriodicRuntimeSemanticsGapAudit",),
        responsibilities=("rotation_dd_periodic_runtime_semantics_gap_audit",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Canonical lower-snake-case skill identity is authoritative. Numeric ESO "
            "ability IDs remain repository crosswalk evidence only. Missing or unknown "
            "periodic identity remains unresolved rather than being inferred from names, "
            "durations, or tooltip prose."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_runtime_evidence",
        domain="rotation",
        purpose=(
            "Inspect imported ESO Logs cast and tick timestamps as non-executable "
            "observational evidence for DD periodic runtime semantics."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_runtime_evidence_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsLogEvent",
            "RotationDDPeriodicRuntimeSemanticsReviewEntry",
        ),
        outputs=("RotationDDPeriodicEsoLogsRuntimeEvidenceReport",),
        responsibilities=("rotation_dd_periodic_esologs_runtime_evidence",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only evidence probe. Translated ESO Logs ability names outrank numeric "
            "ability-id aliases when both are present. Observed timing never promotes "
            "refresh-boundary or magnitude-policy semantics automatically."
        ),
    ),
)


__all__ = ["ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS"]
