from __future__ import annotations

"""Explicit Team Prescription service catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit dependency
wiring; this module is for discovery, validation, and architectural ownership.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="comp.builder.novelty_evidence",
        domain="comp",
        purpose="Derive descriptive candidate rarity from curated ESO Logs observations without turning novelty into a hard validity rule.",
        implementation_path="services.comp_builder_novelty_evidence",
        inputs=("CompBuildCandidate", "ObservedTeamTemplateStore"),
        outputs=("CompNoveltyEvidenceResult",),
        dependencies=("comp.builder.build_candidates",),
        responsibilities=("comp_builder_novelty_evidence",),
        behavior=ServiceBehavior.CALIBRATED,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("Curated ESO Logs team observations",),
        notes="Novelty is descriptive evidence only; hard validity, provider coverage, and candidate gates must win before novelty can influence selection.",
    ),
    ServiceDescriptor(
        service_id="team.prescription.saved_build_generator",
        domain="team",
        purpose="Generate a non-destructive prescribed roster from compatible saved-player anchors while leaving open chairs explicit.",
        implementation_path="services.team_prescription_generator",
        inputs=("PlayerBuild", "TeamPrescriptionScope", "RosterSlotLabels"),
        outputs=("PrescribedRoster",),
        responsibilities=("team_prescription_saved_build_generation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Compatible saved builds are anchors, not proof of optimal class, race, gear, or loadout; open chairs remain unresolved instead of being fabricated.",
    ),
    ServiceDescriptor(
        service_id="team.prescription.provider_coverage_projection",
        domain="team",
        purpose="Project authoritative provider assignments into a prescribed roster without choosing or reassigning providers.",
        implementation_path="services.team_prescription_provider_coverage",
        inputs=("PrescribedRoster", "ProviderAssignment"),
        outputs=("ProviderCoveragePrescriptionResult",),
        responsibilities=("team_prescription_provider_coverage_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Phase 11 provider assignments remain authoritative; unresolved, conflicting, insufficient, or external provider references remain explicit hard constraints.",
    ),
    ServiceDescriptor(
        service_id="team.prescription.slot_constraints",
        domain="team",
        purpose="Apply user-required class and gear ingredients as hard eligibility constraints on prescribed roster chairs.",
        implementation_path="services.team_prescription_slot_constraints",
        inputs=("PrescribedRoster", "PrescribedSlotBuildConstraint", "PlayerBuild"),
        outputs=("PrescribedRoster",),
        responsibilities=("team_prescription_slot_build_constraints",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Injected class or gear requirements are hard gates, never scoring bonuses; missing evidence never satisfies a required ingredient.",
    ),
)


__all__ = ["TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS"]
