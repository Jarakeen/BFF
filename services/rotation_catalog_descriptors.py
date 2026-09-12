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
        service_id="rotation.runtime.combat_state_projection",
        domain="rotation",
        purpose=(
            "Project authoritative ordered runtime history into CombatState at an exact "
            "time/sequence on a concrete rotation plan using the canonical active-bar path."
        ),
        implementation_path="services.rotation_plan_runtime_combat_state_service",
        inputs=(
            "PlayerBuild",
            "CharacterProgression",
            "RotationPlan",
            "ExtremeRuntimeSnapshot",
            "CombatState",
        ),
        outputs=("RotationPlanRuntimeCombatStateResult",),
        responsibilities=("rotation_time_resolved_runtime_combat_state_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Reuses RotationActiveBarAssessor and the shared runtime-snapshot CombatState "
            "projector. Time-varying evaluation requires authoritative runtime_history; "
            "legacy one-snapshot attempts/potion elapsed evidence is not time-shifted."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.runtime.build_context_projection",
        domain="rotation",
        purpose=(
            "Rebuild the canonical active-bar BuildCalculationContext from exact-time "
            "rotation runtime CombatState so derived sheet/core stats match that instant."
        ),
        implementation_path="services.rotation_plan_runtime_build_context_service",
        inputs=(
            "PlayerBuild",
            "RotationPlanRuntimeCombatStateResult",
            "RotationStaticBuildContextService",
        ),
        outputs=("RotationPlanRuntimeBuildContextResult",),
        dependencies=("rotation.runtime.combat_state_projection",),
        responsibilities=("rotation_time_resolved_runtime_build_context_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Rebuilds through the existing static context factory instead of replacing "
            "CombatState on a stale context, because transient buffs can alter derived "
            "character/core stats used by healer and damage coefficient math."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.generate.candidate_resolvers",
        domain="rotation",
        purpose=(
            "Compose Generate-time recovery candidate evaluators and final scorecard "
            "resolvers from the exact seed plan using canonical sustain, duration, "
            "scorecard, and ranking services."
        ),
        implementation_path="services.rotation_generate_candidate_resolver_service",
        inputs=(
            "PlayerBuild",
            "RotationPlan",
            "ResourceType",
            "RotationCandidateSharedEvaluationContext",
        ),
        outputs=("RotationGenerateCandidateResolvers",),
        responsibilities=("rotation_generate_candidate_resolver_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only. Encounter obligations and recovery policy remain explicit "
            "caller evidence; this service does not invent thresholds or strategy facts."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.channel_runtime",
        domain="rotation",
        purpose=(
            "Expand explicitly reviewed channel-heal timing evidence into exact channel "
            "tick events without inferring cadence from total channel duration."
        ),
        implementation_path="services.rotation_healer_channel_runtime_service",
        inputs=(
            "RotationHealerChannelHealSeed",
            "RotationHealerChannelRuntimeEvidence",
            "OptionalRotationHealerChannelMagnitudeResolver",
        ),
        outputs=("RotationHealerChannelRuntimeProjection",),
        responsibilities=("rotation_healer_channel_tick_runtime_projection",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Channel duration, tick cadence, first-tick placement, end-boundary behavior, "
            "and magnitude timing remain separate evidence facts. The scheduler never "
            "derives tick cadence from generic action occupancy or channel duration."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.channel_runtime_evidence",
        domain="rotation",
        purpose=(
            "Join canonical ESO channel duration to separately reviewed healer tick cadence "
            "without allowing reviewed metadata to override imported channel time."
        ),
        implementation_path=(
            "services.rotation_healer_channel_runtime_evidence_service"
        ),
        inputs=(
            "RotationSkillTimingEvidence",
            "RotationHealerReviewedChannelObservation",
        ),
        outputs=("RotationHealerChannelRuntimeEvidence",),
        dependencies=(),
        responsibilities=("rotation_healer_channel_runtime_evidence_join",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Canonical channel_time owns channel duration. Reviewed evidence owns tick "
            "interval, first-tick placement, end-boundary behavior, and magnitude policy. "
            "Missing evidence on either side remains unresolved."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.canonical_demand_evidence",
        domain="rotation",
        purpose=(
            "Compose canonical healer action, periodic, delayed, channel, special-activation, "
            "external-condition, and encounter-window services into candidate-specific "
            "healing evidence."
        ),
        implementation_path="services.rotation_candidate_healer_role_output_service",
        inputs=(
            "GeneratedRotationCandidate",
            "PlayerBuild",
            "BuildCalculationContext",
            "BuildCalculationContextByBar",
            "RotationDemandWindow",
            "RotationHealerReviewedRuntimeObservation",
            "RotationHealerDelayedRuntimeEvidence",
            "RotationHealerChannelRuntimeEvidence",
            "RotationHealerReviewedChannelObservation",
            "RotationSkillTimingEvidenceService",
            "RotationHealerExternalConditionalDemandAssumption",
        ),
        outputs=("RotationHealerDemandHealingEvidence",),
        dependencies=(
            "rotation.candidate_generation",
            "rotation.healer.channel_runtime",
            "rotation.healer.channel_runtime_evidence",
        ),
        responsibilities=("rotation_healer_canonical_demand_evidence",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only: missing first-tick, expiry, refresh, delay, channel cadence, "
            "special activation, or explicitly requested bar-specific static context remains "
            "unresolved rather than being inferred. Canonical channel duration is resolved "
            "from skill timing evidence rather than copied from reviewed cadence metadata."
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
    ServiceDescriptor(
        service_id="rotation.healer.stabilized_runtime_role_output",
        domain="rotation",
        purpose=(
            "Bind final stabilized recovery candidates to exact-time runtime build-context "
            "projection before canonical healer role-output evaluation."
        ),
        implementation_path="services.rotation_recovery_healer_role_output_service",
        inputs=(
            "RecoveryHeavyStabilizedCandidateSnapshot",
            "PlayerBuild",
            "RotationCandidateHealerRoleOutputService",
            "RotationPlanRuntimeBuildContextService",
        ),
        outputs=("RotationCandidateRoleOutputEvidence",),
        dependencies=(
            "rotation.runtime.build_context_projection",
            "rotation.healer.role_output",
        ),
        responsibilities=("rotation_healer_final_stabilized_runtime_role_output",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Runtime context is bound only after recovery stabilization so moved casts and "
            "bar swaps are evaluated on the plan actually ranked. Snapshots without "
            "authoritative runtime history retain the static healer-output path."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.multi_demand_role_output",
        domain="rotation",
        purpose=(
            "Evaluate one healer candidate across multiple explicit encounter healing "
            "windows while preserving each window and exposing a weakest-window floor."
        ),
        implementation_path=(
            "services.rotation_candidate_healer_multi_demand_role_output_service"
        ),
        inputs=(
            "GeneratedRotationCandidate",
            "RotationDemandWindow",
            "RotationHealerDemandHealingEvidence",
        ),
        outputs=(
            "RotationCandidateHealerMultiDemandOutput",
            "RotationCandidateRoleOutputEvidence",
        ),
        dependencies=(
            "rotation.healer.canonical_demand_evidence",
            "rotation.healer.role_output",
        ),
        responsibilities=("rotation_healer_multi_demand_role_output",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The comparison scalar is the lowest resolved modeled-healing-per-demand-second "
            "value across required healing windows. It is not an averaged score, required-HPS "
            "threshold, or survival claim; unresolved evidence in any window fails closed."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.demand_criteria",
        domain="rotation",
        purpose=(
            "Assess provenance-bearing healer encounter criteria against canonical "
            "per-window modeled output without inventing thresholds."
        ),
        implementation_path="services.rotation_healer_demand_criteria_service",
        inputs=(
            "RotationCandidateHealerMultiDemandOutput",
            "RotationHealerDemandCriterion",
        ),
        outputs=("RotationHealerDemandCriteriaAssessment",),
        dependencies=("rotation.healer.multi_demand_role_output",),
        responsibilities=("rotation_healer_demand_criteria_evaluation",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only verified encounter evidence may form a hard healer obligation. "
            "Caller assumptions remain diagnostic; missing canonical window output "
            "fails closed for authoritative criteria."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.criteria_hard_gate",
        domain="rotation",
        purpose=(
            "Project verified healer demand-criterion assessments into the explicit "
            "role hard-obligation channel consumed by recommendation eligibility."
        ),
        implementation_path="services.rotation_healer_demand_criteria_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationCandidateHealerMultiDemandRoleOutputService",
            "RotationHealerDemandCriterion",
        ),
        outputs=("RotationCandidateRoleHardObligationEvidence",),
        dependencies=("rotation.healer.demand_criteria",),
        responsibilities=("rotation_healer_verified_criteria_hard_gate",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Verified failures return a resolved hard-gate failure; unresolved verified "
            "criteria fail closed. Caller-assumption criteria never enter this gate."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.encounter_criteria_provider",
        domain="rotation",
        purpose=(
            "Project explicitly reviewed structured encounter evidence facts into healer "
            "demand criteria while preserving the encounter review/promotion boundary."
        ),
        implementation_path="services.rotation_healer_encounter_criteria_provider",
        inputs=(
            "EncounterService",
            "EncounterEvidenceFact",
            "ReviewedFactId",
        ),
        outputs=("RotationHealerEncounterCriteriaProjection",),
        dependencies=("rotation.healer.demand_criteria",),
        responsibilities=("rotation_healer_reviewed_encounter_criteria_projection",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only explicit healer_demand_criterion facts are read. Reconciliation alone "
            "does not promote a fact: an exact reviewed fact id is required before the "
            "criterion becomes VERIFIED_ENCOUNTER_EVIDENCE."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.encounter_demand_bundle",
        domain="rotation",
        purpose=(
            "Compose reviewed health-threshold clock projection, explicit healer demand "
            "policy, and encounter-backed healer criteria into one encounter input bundle."
        ),
        implementation_path="services.rotation_healer_encounter_demand_bundle_service",
        inputs=(
            "EncounterBossGuide",
            "RaidDamageSegment",
            "EncounterThresholdRotationDemandPolicy",
            "ReviewedFactId",
        ),
        outputs=("RotationHealerEncounterDemandBundle",),
        dependencies=(
            "rotation.healer.encounter_criteria_provider",
        ),
        responsibilities=("rotation_healer_encounter_demand_bundle_composition",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only. Health thresholds own encounter timing facts, raid-damage "
            "trajectory owns projected clock time, role policy owns preparation windows, "
            "and reviewed criterion evidence owns any numeric healer hard gate."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.caster_healing_relevance",
        domain="rotation",
        purpose=(
            "Classify reviewed canonical skill identities by whether their activation has "
            "caster-owned healing, no caster-owned healing, or an external conditional "
            "healing path that requires separate modeling."
        ),
        implementation_path="services.rotation_healer_caster_healing_relevance_service",
        inputs=("CanonicalSkillSemanticId",),
        outputs=("RotationHealerCasterHealingRelevanceEvidence",),
        dependencies=(),
        responsibilities=("rotation_healer_skill_caster_healing_relevance",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Reviewed no-caster-healing identities may bypass healer tooltip projection. "
            "External conditional healing remains explicit and unresolved until its trigger "
            "path is modeled. Unknown skill identities continue fail-closed."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.external_conditional_healing_evidence",
        domain="rotation",
        purpose=(
            "Expose reviewed external-condition healer effect duration, per-trigger magnitude, "
            "trigger actor, recipient, log-credit owner, and maximum per-actor rate."
        ),
        implementation_path="services.rotation_healer_external_conditional_healing_service",
        inputs=("CanonicalSkillSemanticId", "GameVersion"),
        outputs=("RotationHealerExternalConditionalHealingEvidence",),
        dependencies=("rotation.healer.caster_healing_relevance",),
        responsibilities=("rotation_healer_external_conditional_healing_evidence",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Minor Lifesteal retains damage-trigger and ownership semantics separately from "
            "strategy participation. Demand projection requires an explicit active-attacker "
            "count and does not fabricate periodic heal events."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.minor_lifesteal_esologs_evidence",
        domain="rotation",
        purpose=(
            "Extract candidate Minor Lifesteal heal aliases, actor ownership, preceding "
            "same-source damage, and per-actor cadence from read-only ESO Logs events."
        ),
        implementation_path=(
            "services.rotation_healer_minor_lifesteal_esologs_evidence_service"
        ),
        inputs=(
            "EsoLogsSqlitePath",
            "OptionalReportFightFilter",
            "ObservationalHealAbilityAliases",
        ),
        outputs=("RotationHealerMinorLifestealEsoLogsEvidenceReport",),
        dependencies=("rotation.healer.external_conditional_healing_evidence",),
        responsibilities=("rotation_healer_minor_lifesteal_runtime_evidence_discovery",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Output remains candidate evidence. Numeric ids are observational aliases; "
            "observed intervals and preceding damage are not promoted to cooldown or "
            "trigger rules without explicit human review."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.healer.output_context_relevance",
        domain="rotation",
        purpose=(
            "Classify broad static build-context diagnostics by whether they can invalidate "
            "modeled healer output, preserving unknown diagnostics fail-closed."
        ),
        implementation_path="services.rotation_healer_output_context_relevance_service",
        inputs=("BuildCalculationContextUnresolved",),
        outputs=("RotationHealerOutputContextRelevance",),
        dependencies=(),
        responsibilities=("rotation_healer_output_context_unresolved_relevance",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Only diagnostics whose non-healing role is already established are ambient. "
            "Charged status chance is ambient to raw modeled healing but remains available "
            "to support/damage objectives. Potion activation and unknown diagnostics remain "
            "healer-output relevant until explicitly resolved."
        ),
    ),
)


__all__ = ["ROTATION_SERVICE_DESCRIPTORS"]
