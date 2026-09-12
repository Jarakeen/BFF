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
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_secondary_effect_discovery",
        domain="rotation",
        purpose=(
            "Discover and rank secondary ESO Logs damage identities that repeatedly "
            "occur after a canonical DD periodic skill cast."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_secondary_effect_discovery_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsLogEvent",
            "RotationDDPeriodicRuntimeSemanticsReviewEntry",
        ),
        outputs=("RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport",),
        responsibilities=("rotation_dd_periodic_esologs_secondary_effect_discovery",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only candidate discovery for combat-log cases where a cast and its "
            "periodic damage use different event identities. Candidate ranking may use "
            "cast-track linkage and reviewed cadence, but never promotes executable "
            "runtime semantics automatically."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_reviewed_coverage",
        domain="rotation",
        purpose=(
            "Report which reviewed DD periodic skill identities have matching cast "
            "observations in an imported ESO Logs corpus."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_reviewed_coverage_service"
        ),
        inputs=(
            "RotationDDPeriodicRuntimeSemanticsReviewEntry",
            "RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryReport",
        ),
        outputs=("RotationDDPeriodicEsoLogsReviewedCoverageReport",),
        responsibilities=("rotation_dd_periodic_esologs_reviewed_coverage",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Composition-only corpus triage. It reuses reviewed canonical identities and "
            "the existing secondary-effect discovery parser, ranks observed skills first, "
            "and never promotes observational evidence into executable runtime semantics."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_anchor_correlation",
        domain="rotation",
        purpose=(
            "Measure observational cast-to-impact and impact-to-periodic timing for a "
            "canonical DD skill using reviewed ESO Logs evidence IDs."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_anchor_correlation_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsImpactAbilityId",
            "EsoLogsPeriodicAbilityId",
            "EsoLogsLogEvent",
        ),
        outputs=("RotationDDPeriodicEsoLogsAnchorCorrelationReport",),
        responsibilities=("rotation_dd_periodic_esologs_anchor_correlation",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only evidence correlation. Numeric impact/periodic IDs are explicit "
            "evidence handles, never canonical identities. Correlation may nominate an "
            "impact activation anchor and offset but never promotes semantics automatically."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_replay_anchor_mapping",
        domain="rotation",
        purpose=(
            "Map exact cast-track-linked ESO Logs cast/impact observations onto exact "
            "rotation replay actions and emit semantic activation-anchor evidence."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_replay_anchor_mapping_service"
        ),
        inputs=(
            "RotationPlan",
            "RotationDDPeriodicEsoLogsCastImpactObservation",
            "ReplayOriginTimestamp",
        ),
        outputs=(
            "RotationDDPeriodicEsoLogsReplayAnchorMappingResult",
            "RotationRuntimeActivationAnchorEvidence",
        ),
        responsibilities=("rotation_dd_periodic_esologs_replay_anchor_mapping",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Replay-only bridge. Matching requires exact plan time, canonical skill identity, "
            "and cast-track-linked observation provenance. It never searches for a nearest "
            "action or promotes aggregate cast-to-impact delay statistics into future timing."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_refresh_boundary_evidence",
        domain="rotation",
        purpose=(
            "Observe cast-track-linked old periodic events around the next reviewed "
            "activation impact to support DD refresh-boundary review."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_refresh_boundary_evidence_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsImpactAbilityId",
            "EsoLogsPeriodicAbilityId",
            "EsoLogsCastTrackId",
            "EsoLogsLogEvent",
        ),
        outputs=("RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceReport",),
        responsibilities=("rotation_dd_periodic_esologs_refresh_boundary_evidence",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only boundary evidence. Replacement is measured at the reviewed "
            "activation event, not blindly at button press. Numeric IDs remain evidence "
            "handles and the probe never promotes executable refresh policy automatically."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_magnitude_observation",
        domain="rotation",
        purpose=(
            "Observe same-cast periodic damage amounts under fixed target and hit-type "
            "grouping to support DD snapshot-vs-dynamic magnitude review."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_magnitude_observation_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsPeriodicAbilityId",
            "EsoLogsCastTrackId",
            "EsoLogsTargetId",
            "EsoLogsHitType",
            "EsoLogsDamageAmount",
        ),
        outputs=("RotationDDPeriodicEsoLogsMagnitudeObservationReport",),
        responsibilities=("rotation_dd_periodic_esologs_magnitude_observation",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only magnitude evidence. Target and hit type are separated to avoid "
            "obvious confounders, but amount variation still cannot promote snapshot or "
            "dynamic magnitude policy without combat-state review. Numeric IDs remain "
            "observational evidence handles only."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.periodic_esologs_magnitude_state_transition",
        domain="rotation",
        purpose=(
            "Correlate same-cast periodic amount changes with observed source or target "
            "buff/debuff transitions to strengthen snapshot-vs-dynamic magnitude review."
        ),
        implementation_path=(
            "services.rotation_dd_periodic_esologs_magnitude_state_transition_service"
        ),
        inputs=(
            "CanonicalSkillIdentity",
            "EsoLogsPeriodicAbilityId",
            "EsoLogsCastTrackId",
            "EsoLogsTargetId",
            "EsoLogsHitType",
            "EsoLogsDamageAmount",
            "EsoLogsBuffDebuffEvent",
        ),
        outputs=("RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport",),
        responsibilities=("rotation_dd_periodic_esologs_magnitude_state_transition",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only state-transition evidence. Only buff/debuff events targeting the "
            "damage source or damage target between consecutive same-cast ticks are "
            "reported. Correlation can strengthen magnitude-policy review but never "
            "promotes executable semantics automatically. Numeric IDs remain evidence handles."
        ),
    ),
)


__all__ = ["ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS"]
