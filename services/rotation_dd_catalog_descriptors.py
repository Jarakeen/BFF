from __future__ import annotations

"""Whole-plan DD Rotation Builder service catalog metadata."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ROTATION_DD_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.dd.whole_plan_damage_coverage_audit",
        domain="rotation",
        purpose=(
            "Count resolved and unresolved scheduled DD damage consequences for one exact "
            "candidate and group repeated canonical blockers without reinterpreting them."
        ),
        implementation_path=(
            "services.rotation_dd_whole_plan_damage_coverage_audit_service"
        ),
        inputs=(
            "GeneratedRotationCandidate",
            "RotationActionDamageEvidenceProvider",
        ),
        outputs=("RotationDDWholePlanDamageCoverageAudit",),
        responsibilities=("rotation_dd_whole_plan_damage_coverage_audit",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Audit only. The existing action-damage provider remains authoritative for "
            "damage consequences. Missing mechanics stay unresolved; blocker grouping "
            "preserves every exact time/sequence occurrence for countable closeout work."
        ),
    ),
)


__all__ = ["ROTATION_DD_SERVICE_DESCRIPTORS"]
