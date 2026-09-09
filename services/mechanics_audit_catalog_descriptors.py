from __future__ import annotations

"""Encounter-evidence ingestion and shared mechanics-readiness catalog descriptors.

Metadata only. These entries describe evidence projection and coverage auditing; they
do not promote source observations into canonical mechanics or provide runtime lookup.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


MECHANICS_AUDIT_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="encounter.boss_source.evidence_projection",
        domain="encounter",
        purpose="Project tracked boss-source JSON into source-qualified encounter evidence packets for reconciliation and review without promoting source rows into canonical encounter truth.",
        implementation_path="services.boss_encounter_projection",
        inputs=("BossSourceJson", "SourcePath"),
        outputs=("BossEncounterProjection", "EncounterEvidence", "EncounterEvidencePacket"),
        responsibilities=("encounter_boss_source_evidence_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("Tracked UESP boss-source corpus",),
        notes="The source corpus is evidence, not canonical truth. Projection stops before canonical persistence; inferred and incomplete mechanics remain explicitly marked for reconciliation, review, and promotion policy.",
    ),
    ServiceDescriptor(
        service_id="mechanics.coverage.audit",
        domain="mechanics",
        purpose="Audit explicit mechanics-coverage observations into decision-scoped readiness evidence and a shared canonical-knowledge research queue.",
        implementation_path="services.canonical_mechanics_coverage_audit",
        inputs=("CanonicalMechanicsCoverageEvidence", "DeclaredMechanicsDependencies"),
        outputs=("CanonicalMechanicsCoverageReport", "CanonicalKnowledgeGap"),
        responsibilities=("canonical_mechanics_coverage_audit",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Coverage metadata records what BFF can currently prove; it is not ESO mechanics itself. PARTIAL and NICHE gaps remain advisory, MISSING_CRITICAL gaps block only dependent decisions, and undeclared/missing dependency coverage fails closed without globally disabling unrelated consumers.",
    ),
)


__all__ = ["MECHANICS_AUDIT_SERVICE_DESCRIPTORS"]
