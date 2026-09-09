from __future__ import annotations

"""Encounter-domain service catalog descriptors.

Metadata only. These entries document encounter truth, explicit overlays, and the
provider-candidate/suitability/assignment chain without making the catalog a runtime
service locator.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ENCOUNTER_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="encounter.domain_read_model",
        domain="encounter",
        purpose="Expose read-only canonical encounter definitions, structured player requirements, target/positioning constraints, and reconciled evidence without inferring mechanics from prose.",
        implementation_path="services.encounter_service",
        inputs=("EncounterRepository", "EncounterId", "Difficulty", "PhaseId"),
        outputs=("EncounterDefinition", "EncounterRequirement", "EncounterTargetConstraint", "EncounterPositioningConstraint", "EncounterTemporalEvidence"),
        dependencies=("encounter.repository",),
        responsibilities=("canonical_encounter_domain_read_model",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Only explicit structured fields become requirements or constraints. Missing target counts, unresolved thresholds, prose hints, and source conflicts remain unresolved rather than being guessed into canonical truth.",
    ),
    ServiceDescriptor(
        service_id="encounter.requirement_overlay",
        domain="encounter",
        purpose="Append explicitly supplied analysis-context requirements to canonical encounter requirements without mutating or replacing the canonical encounter source.",
        implementation_path="services.encounter_requirement_overlay",
        inputs=("EncounterService", "ExplicitAdditionalRequirements"),
        outputs=("EncounterRequirement",),
        dependencies=("encounter.domain_read_model",),
        responsibilities=("explicit_encounter_requirement_overlay",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="The canonical encounter service remains authoritative for boss mechanics. Overlay requirements must come from another explicit source and may not collide with canonical requirement identities.",
    ),
    ServiceDescriptor(
        service_id="encounter.provider.candidate_projection",
        domain="encounter",
        purpose="Project authoritative Phase 10 provider evidence into exact per-requirement Phase 11 candidate sets without rescanning builds or choosing a provider.",
        implementation_path="services.encounter_provider_candidate",
        inputs=("EncounterRosterEvaluationReport", "SavedBuildCapabilityAudit"),
        outputs=("ProviderCandidateSet",),
        dependencies=("build.saved_capability_analysis",),
        responsibilities=("encounter_provider_candidate_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Provider, unresolved, and conflict membership from Phase 10 is authoritative. This layer binds that exact evidence to canonical requirements; names, tooltip prose, roster order, and fresh build inference are not substitutes.",
    ),
    ServiceDescriptor(
        service_id="encounter.provider.suitability",
        domain="encounter",
        purpose="Aggregate explicit source-backed suitability facts for already-viable provider candidates without changing capability truth or selecting a provider.",
        implementation_path="services.encounter_provider_suitability",
        inputs=("ProviderCandidateSet", "ProviderSuitabilityEvidence"),
        outputs=("ProviderSuitabilitySet",),
        dependencies=("encounter.provider.candidate_projection",),
        responsibilities=("encounter_provider_suitability_assessment",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Suitability is not capability. Favorable Phase 11 facts cannot make unresolved or conflicting Phase 10 candidates viable; conflicting assessments for the same dimension are rejected rather than collapsed.",
    ),
    ServiceDescriptor(
        service_id="encounter.provider.assignment",
        domain="encounter",
        purpose="Choose primary encounter providers only when capability and optional suitability evidence leave a unique defensible assignment, otherwise preserve the unresolved state.",
        implementation_path="services.encounter_provider_assignment",
        inputs=("ProviderCandidateSet", "ProviderSuitabilitySet"),
        outputs=("ProviderAssignment",),
        dependencies=("encounter.provider.candidate_projection", "encounter.provider.suitability"),
        responsibilities=("encounter_provider_assignment",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Roster order is never a tie-break. Unknown suitability is not a silent positive, conflicting capability blocks assignment, and ambiguous selections remain unresolved instead of being guessed.",
    ),
    ServiceDescriptor(
        service_id="encounter.provider.responsibility_audit",
        domain="encounter",
        purpose="Audit assigned providers for explicit source-backed double-duty conflicts between exact encounter requirements.",
        implementation_path="services.encounter_provider_responsibility",
        inputs=("ProviderAssignment", "ProviderResponsibilityConflictEvidence"),
        outputs=("ProviderResponsibilityAudit",),
        dependencies=("encounter.provider.assignment",),
        responsibilities=("encounter_provider_responsibility_conflict_audit",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="A player appearing on multiple provider rows is not itself a conflict. Double-duty conflicts exist only when explicit evidence says the same member cannot carry the exact pair of requirements together.",
    ),
)


__all__ = ["ENCOUNTER_SERVICE_DESCRIPTORS"]
