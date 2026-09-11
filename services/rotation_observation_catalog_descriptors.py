from __future__ import annotations

"""Discovery metadata for Rotation Builder observation/review responsibilities."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ROTATION_OBSERVATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.healer.periodic_observation_review",
        domain="rotation",
        purpose=(
            "Promote only explicitly selected human-reviewed healer periodic runtime "
            "observation candidates into a separate reviewed fixture."
        ),
        implementation_path="services.rotation_healer_periodic_observation_review_service",
        inputs=("CandidateObservationFixture", "ApprovedSampleIndex", "ReviewNote"),
        outputs=("ReviewedObservationFixture",),
        responsibilities=("rotation_healer_periodic_observation_review_promotion",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Extraction success never implies approval. Candidate fixtures remain unchanged; "
            "promotion requires explicit sample indices and review provenance. Refresh/recast "
            "semantics remain a separate evidence responsibility."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.periodic_observation_consensus",
        domain="rotation",
        purpose=(
            "Derive one conservative runtime observation from repeated explicitly reviewed "
            "isolated healer periodic samples without hiding conflicting evidence."
        ),
        implementation_path="services.rotation_healer_periodic_observation_consensus_service",
        inputs=("ReviewedObservationFixtureEntry",),
        outputs=("ReviewedRuntimeObservationConsensus",),
        responsibilities=("rotation_healer_periodic_observation_consensus",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "First-tick placement uses the median of agreeing reviewed measurements and retains "
            "their observed range and provenance. Conflicting runtime/cadence or expiry-boundary "
            "evidence fails closed. Refresh/recast semantics remain separate and are not inferred."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.periodic_recast_observation_audit",
        domain="rotation",
        purpose=(
            "Inspect overlapping healer HoT recasts against reviewed single-application timing "
            "to surface restart-shaped or timing-ambiguous observational evidence."
        ),
        implementation_path="tools.audit_phase13_healer_recast_observation_candidates",
        inputs=(
            "EsoLogsRawExport",
            "ReviewedObservationFixture",
            "CanonicalPeriodicTiming",
            "ReviewedPeriodicEffectAliases",
        ),
        outputs=("RecastObservationCandidateAudit",),
        responsibilities=("rotation_healer_periodic_recast_observation_audit",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only recipient-aware evidence inspection only. Restart-shaped timing is not "
            "promotion. Periodic phase comparisons are cadence-aware and ambiguous phase collisions "
            "remain unresolved rather than being mistaken for coexistence."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.refresh_evidence_window_discovery",
        domain="rotation",
        purpose=(
            "Search an ESO Logs research corpus for the strongest same-recipient healer HoT recast "
            "windows to prioritize targeted human review of unresolved refresh semantics."
        ),
        implementation_path="tools.discover_phase13_healer_refresh_evidence_windows",
        inputs=(
            "EsoLogsResearchCorpus",
            "ReviewedObservationFixture",
            "CanonicalPeriodicTiming",
            "ReviewedPeriodicEffectAliases",
        ),
        outputs=("RankedRefreshEvidenceWindows",),
        responsibilities=("rotation_healer_refresh_evidence_window_discovery",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Read-only discovery only. Windows are ranked by recipient-level timing shape and "
            "phase separability so ambiguous recasts do not dominate review. Discovery output "
            "is candidate evidence and cannot promote a refresh policy."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.periodic_refresh_policy_review",
        domain="rotation",
        purpose=(
            "Load explicitly human-reviewed healer periodic refresh/recast policies from a "
            "separate fixture and compose exact identity/version matches into reviewed timing evidence."
        ),
        implementation_path="services.rotation_healer_periodic_refresh_policy_fixture_service",
        inputs=("ReviewedRuntimeObservation", "ReviewedRefreshPolicyFixture"),
        outputs=("ReviewedRuntimeObservationWithRefreshPolicy",),
        responsibilities=("rotation_healer_periodic_refresh_policy_review",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "No policy is inferred from logs. Refresh-policy review remains separate from isolated "
            "timing review; candidate audit output cannot be consumed as reviewed policy evidence."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.reviewed_runtime_evidence_composition",
        domain="rotation",
        purpose=(
            "Compose reviewed healer periodic timing consensus with separately reviewed refresh/recast "
            "policy evidence into consumer-ready runtime observations."
        ),
        implementation_path="services.rotation_healer_reviewed_runtime_evidence_loader",
        inputs=("ReviewedObservationFixture", "ReviewedRefreshPolicyFixture"),
        outputs=("ReviewedRuntimeObservation",),
        responsibilities=("rotation_healer_reviewed_runtime_evidence_composition",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Composition requires exact skill/component/version matches. Missing or unmatched reviewed "
            "evidence remains unresolved; the loader does not infer timing or refresh policy."
        ),
    ),
)


__all__ = ["ROTATION_OBSERVATION_SERVICE_DESCRIPTORS"]
