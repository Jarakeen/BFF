from __future__ import annotations

"""Explicit Tank rotation service catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit dependency
wiring; the catalog remains a discovery index rather than a service locator.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_TANK_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.tank.taunt_application_obligation",
        domain="rotation",
        purpose=(
            "Assess an explicit tank taunt-application obligation against canonical "
            "skill-component TAUNT utility evidence and the exact scheduled rotation plan."
        ),
        implementation_path="services.rotation_tank_taunt_obligation_service",
        inputs=(
            "RotationPlan",
            "RotationTankTauntApplicationRequirement",
            "RotationAction.target_key",
            "SkillCoefficientRepository",
            "SkillComponentUtilityEffectRepository",
        ),
        outputs=("RotationTankTauntApplicationAssessment",),
        responsibilities=("rotation_tank_taunt_application_hard_obligation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The requirement must explicitly supply source skill, timing window, minimum "
            "application count, optional bar, and optional target identity. Canonical TAUNT "
            "utility proves only that the scheduled skill applies taunt. When a target_key is "
            "supplied, only an exact matching scheduled target counts. The service does not "
            "infer target identity, taunt duration, continuous uptime, immunity/overtaunt "
            "behavior, or survivability."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_duration",
        domain="rotation",
        purpose=(
            "Resolve source-backed tank taunt duration only when canonical TAUNT identity and "
            "canonical temporal evidence agree unambiguously, without creating refresh policy."
        ),
        implementation_path="services.rotation_tank_taunt_duration_service",
        inputs=(
            "SkillCoefficientRepository",
            "SkillComponentUtilityEffectRepository",
            "RotationDurationResolution",
        ),
        outputs=("RotationTankTauntDurationResolution",),
        responsibilities=("rotation_tank_taunt_duration_evidence",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The strongest path binds duration directly to coefficient-owned text that also proves "
            "TAUNT identity; generic duration evidence is only a conservative fallback. A resolved "
            "duration is evidence only and does not imply recast cadence, safety margin, continuous "
            "ownership, immunity, or overtaunt semantics."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_maintenance_obligation",
        domain="rotation",
        purpose=(
            "Assess continuous target-specific tank taunt ownership across an explicit reviewed "
            "responsibility window using canonical taunt duration and exact scheduled casts."
        ),
        implementation_path="services.rotation_tank_taunt_maintenance_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntMaintenanceRequirement",
            "RotationTankTauntDurationResolution",
            "RotationAction.target_key",
        ),
        outputs=(
            "RotationTankTauntMaintenanceAssessment",
            "RotationCandidateRoleHardObligationEvidence",
        ),
        dependencies=("rotation.tank.taunt_duration",),
        responsibilities=("rotation_tank_target_specific_taunt_maintenance_hard_obligation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The requirement explicitly owns target identity and the active responsibility window. "
            "Only exact matching source-skill casts on that target contribute canonical-duration "
            "coverage. Any uncovered interval fails the obligation. The service does not choose "
            "refresh lead, target swaps, overtaunt/immunity behavior, or survivability policy."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.assignment_taunt_obligation",
        domain="rotation",
        purpose=(
            "Translate explicit provider-assignment ownership plus reviewed taunt application "
            "policy into exact tank taunt-application requirements without inventing uptime."
        ),
        implementation_path="services.rotation_assignment_taunt_obligation_service",
        inputs=(
            "CharacterBuild",
            "ProviderAssignment",
            "RotationAssignmentTauntPolicy",
            "RotationAssignmentTauntApplicationWindow",
        ),
        outputs=("RotationAssignmentTauntObligationProjection",),
        dependencies=("rotation.tank.taunt_application_obligation",),
        responsibilities=("rotation_assignment_tank_taunt_application_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Provider assignment proves who owns the responsibility. Policy supplies the exact "
            "source taunt skill and one or more explicit occurrence windows, optionally including "
            "an exact caller-owned target_key. The adapter emits application requirements only; "
            "it does not infer target identity, taunt duration, refresh cadence, continuous "
            "maintenance, or overtaunt/immunity semantics."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.assignment_taunt_maintenance",
        domain="rotation",
        purpose=(
            "Translate explicit provider-assignment ownership plus reviewed continuous target "
            "ownership windows into tank taunt-maintenance requirements."
        ),
        implementation_path="services.rotation_assignment_taunt_maintenance_service",
        inputs=(
            "CharacterBuild",
            "ProviderAssignment",
            "RotationAssignmentTauntMaintenancePolicy",
            "RotationAssignmentTauntMaintenanceWindow",
        ),
        outputs=("RotationAssignmentTauntMaintenanceProjection",),
        dependencies=("rotation.tank.taunt_maintenance_obligation",),
        responsibilities=("rotation_assignment_tank_taunt_maintenance_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Provider assignment proves who owns the target responsibility. Policy supplies the "
            "source-backed taunt skill, exact target_key, and reviewed active windows. Duration "
            "remains canonical mechanic evidence and refresh lead remains separate strategy policy."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.assignment_obligation_bundle",
        domain="rotation",
        purpose=(
            "Compose exact assignment-backed Tank taunt application, continuous taunt ownership, "
            "and reviewed defensive obligations for one encounter/member into one Generate-ready bundle."
        ),
        implementation_path="services.rotation_tank_assignment_obligation_bundle_service",
        inputs=(
            "CharacterBuild",
            "ProviderAssignment",
            "RotationAssignmentTauntPolicy",
            "RotationAssignmentTauntMaintenancePolicy",
            "RotationTankDefensiveObligation",
        ),
        outputs=("RotationTankAssignmentObligationBundle",),
        dependencies=(
            "rotation.tank.assignment_taunt_obligation",
            "rotation.tank.assignment_taunt_maintenance",
            "rotation.tank.defensive_response_obligation",
        ),
        responsibilities=("rotation_tank_assignment_obligation_composition",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This is orchestration only. Provider assignment remains authoritative for ownership; "
            "taunt policy services remain authoritative for taunt semantics; defensive obligations "
            "must already be reviewed. Foreign-encounter policy input fails closed."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_candidate_claim",
        domain="rotation",
        purpose=(
            "Preserve already-satisfied source-backed taunt applications or insert exact "
            "caller-owned taunt skill claims without choosing refresh cadence or displacing "
            "occupied rotation slots."
        ),
        implementation_path="services.rotation_tank_taunt_candidate_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntApplicationRequirement",
            "RotationTankTauntActionClaim",
            "RotationActionSlotRequirement",
            "RotationAction.target_key",
        ),
        outputs=("RotationTankTauntCandidateProjection",),
        dependencies=("rotation.tank.taunt_application_obligation",),
        responsibilities=("rotation_tank_taunt_candidate_generation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "The requirement owns the exact source skill, application window, and optional target "
            "identity; the claim owns action kind, exact time, sequence, optional bar, and may "
            "repeat the same target identity. Existing legal applications are preserved. New "
            "casts require saved-build structural evidence proving the exact skill/Ultimate is "
            "slotted on the selected bar; a two-bar source without an explicit bar remains "
            "unresolved. Conflicting target identities, slots, and missing applications fail "
            "closed. This remains application-only and does not imply duration or maintenance."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_maintenance_candidate",
        domain="rotation",
        purpose=(
            "Fill only real target-specific taunt-maintenance gaps by deriving exact application "
            "claims from canonical duration plus explicit caller-owned refresh strategy."
        ),
        implementation_path="services.rotation_tank_taunt_maintenance_candidate_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntMaintenanceRequirement",
            "RotationTankTauntMaintenanceRefreshPolicy",
            "RotationActionSlotRequirement",
        ),
        outputs=("RotationTankTauntMaintenanceCandidateProjection",),
        dependencies=(
            "rotation.tank.taunt_maintenance_obligation",
            "rotation.tank.taunt_candidate_claim",
        ),
        responsibilities=("rotation_tank_taunt_maintenance_candidate_generation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Existing target-correct coverage is preserved. The caller explicitly owns refresh "
            "lead and any required initial application timestamp. Derived claims never displace "
            "occupied slots and are re-assessed against continuous maintenance after insertion."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_family_projection",
        domain="rotation",
        purpose=(
            "Apply one explicit source-backed taunt requirement/claim policy to each generated "
            "candidate through the role-neutral family projection hook before evaluation."
        ),
        implementation_path="services.rotation_tank_taunt_family_projector_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntApplicationRequirement",
            "RotationTankTauntActionClaim",
            "RotationActionSlotRequirement",
            "RotationCandidateFamilyProjector",
        ),
        outputs=("GeneratedRotationCandidate",),
        dependencies=("rotation.tank.taunt_candidate_claim",),
        responsibilities=("rotation_tank_taunt_family_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Resolved candidates preserve/insert exact taunt applications before family evaluation. "
            "Saved-build slot evidence and any explicit action target identity are carried through. "
            "Candidate-specific projection failures remain on that plan's unresolved channel "
            "instead of aborting otherwise valid sibling candidates."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.taunt_maintenance_family_projection",
        domain="rotation",
        purpose=(
            "Apply target-specific taunt-maintenance requirements and explicit refresh strategy "
            "to each generated candidate through the role-neutral family projection hook."
        ),
        implementation_path="services.rotation_tank_taunt_maintenance_family_projector_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntMaintenanceRequirement",
            "RotationTankTauntMaintenanceRefreshPolicy",
            "RotationActionSlotRequirement",
            "RotationCandidateFamilyProjector",
        ),
        outputs=("GeneratedRotationCandidate",),
        dependencies=("rotation.tank.taunt_maintenance_candidate",),
        responsibilities=("rotation_tank_taunt_maintenance_family_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Maintenance is projected independently per sibling candidate before evaluation. "
            "Candidates that already satisfy ownership are preserved; projection failures stay "
            "candidate-local instead of aborting otherwise valid siblings."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.defensive_response_obligation",
        domain="rotation",
        purpose=(
            "Assess explicit source-backed block/dodge response obligations against the exact "
            "role-neutral rotation schedule without inventing mitigation or encounter timing."
        ),
        implementation_path="services.rotation_tank_defensive_obligation_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankDefensiveObligation",
            "RotationActionKind.BLOCK",
            "RotationActionKind.DODGE",
        ),
        outputs=("RotationCandidateRoleHardObligationEvidence",),
        responsibilities=("rotation_tank_defensive_response_hard_obligation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Allowed response kind, exact response window, minimum count, optional bar, and "
            "provenance are explicit inputs. The service does not infer that a mechanic is "
            "blockable/dodgeable, calculate mitigation, or manufacture timing from guide prose."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_defensive_projection",
        domain="rotation",
        purpose=(
            "Project structured, non-conflicting reviewed encounter evidence into exact "
            "tank block/dodge obligations when a separately supplied occurrence binding "
            "places the mechanic on the rotation clock."
        ),
        implementation_path=(
            "services.rotation_tank_encounter_defensive_obligation_service"
        ),
        inputs=(
            "ReconciledEncounterFact",
            "RotationTankEncounterDefensiveWindowBinding",
        ),
        outputs=("RotationTankEncounterDefensiveProjection",),
        dependencies=("rotation.tank.defensive_response_obligation",),
        responsibilities=("rotation_tank_reviewed_encounter_defensive_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Structured fact fields must explicitly prove both tank applicability and block/"
            "dodge response semantics. The binding owns only occurrence identity and clock "
            "placement. Free-form prose, conflicting facts, and unproven timing fail closed."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_defensive_timing_binding",
        domain="rotation",
        purpose=(
            "Reuse reviewed canonical encounter clock-window projection to bind exact mechanic "
            "occurrences to separately reviewed tank defensive facts without duplicating timing truth."
        ),
        implementation_path="services.rotation_tank_encounter_defensive_timing_service",
        inputs=(
            "EncounterBossGuide",
            "RotationTankEncounterDefensiveTimingPolicy",
            "EncounterRotationDemandService",
        ),
        outputs=("RotationTankEncounterDefensiveTimingProjection",),
        dependencies=("rotation.tank.encounter_defensive_projection",),
        responsibilities=("rotation_tank_reviewed_encounter_defensive_timing_binding",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Canonical encounter timing and defensive-response semantics remain separate evidence "
            "lanes. Reviewed explicit seconds are reused through EncounterRotationDemandService; "
            "health/phase thresholds, missing evidence, and ambiguous timing remain unresolved."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_defensive_bundle",
        domain="rotation",
        purpose=(
            "Compose reviewed explicit-clock Tank defensive occurrences by joining canonical "
            "encounter timing with separately reviewed structured defensive facts."
        ),
        implementation_path="services.rotation_tank_encounter_defensive_bundle_service",
        inputs=(
            "EncounterBossGuide",
            "ReconciledEncounterFact",
            "RotationTankEncounterDefensiveTimingPolicy",
        ),
        outputs=("RotationTankEncounterDefensiveBundle",),
        dependencies=(
            "rotation.tank.encounter_defensive_timing_binding",
            "rotation.tank.encounter_defensive_projection",
        ),
        responsibilities=("rotation_tank_reviewed_explicit_clock_defensive_composition",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This service creates no new mechanic or timing truth. Missing, duplicate, conflicting, "
            "or unreviewed fact identity remains unresolved; resolved obligations are ordered by "
            "their canonical clock windows."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_threshold_defensive_timing_binding",
        domain="rotation",
        purpose=(
            "Reuse projected canonical health-threshold clock windows to bind tank defensive "
            "occurrences without duplicating raid-damage trajectory or threshold timing truth."
        ),
        implementation_path=(
            "services.rotation_tank_encounter_threshold_defensive_timing_service"
        ),
        inputs=(
            "EncounterHealthThresholdProjection",
            "RotationTankEncounterThresholdDefensiveTimingPolicy",
            "EncounterThresholdRotationDemandService",
        ),
        outputs=("RotationTankEncounterDefensiveTimingProjection",),
        dependencies=("rotation.tank.encounter_defensive_projection",),
        responsibilities=(
            "rotation_tank_projected_threshold_defensive_timing_binding",
        ),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reviewed health thresholds are converted to seconds only by the existing explicit "
            "raid-damage trajectory projection. Missing, ambiguous, or unreachable threshold "
            "clock points remain unresolved; this adapter only binds resolved windows to the "
            "separately reviewed defensive mechanic fact."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_threshold_defensive_bundle",
        domain="rotation",
        purpose=(
            "Compose reviewed health-threshold Tank defensive occurrences from the existing "
            "canonical threshold clock projection and separately reviewed defensive facts."
        ),
        implementation_path="services.rotation_tank_encounter_threshold_defensive_bundle_service",
        inputs=(
            "EncounterHealthThresholdProjection",
            "ReconciledEncounterFact",
            "RotationTankEncounterThresholdDefensiveTimingPolicy",
        ),
        outputs=("RotationTankEncounterThresholdDefensiveBundle",),
        dependencies=(
            "rotation.tank.encounter_threshold_defensive_timing_binding",
            "rotation.tank.encounter_defensive_projection",
        ),
        responsibilities=("rotation_tank_reviewed_threshold_defensive_composition",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The canonical EncounterHealthThresholdProjection remains the sole owner of threshold "
            "clock points. This service does not derive raid DPS, boss health, or threshold timing."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.hard_obligation_composition",
        domain="rotation",
        purpose=(
            "Compose all supplied canonical Tank hard responsibilities into the single role-hard-"
            "obligation evidence channel consumed by candidate evaluation."
        ),
        implementation_path="services.rotation_tank_hard_obligation_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankTauntApplicationRequirement",
            "RotationTankTauntMaintenanceRequirement",
            "RotationTankDefensiveObligation",
        ),
        outputs=("RotationCandidateRoleHardObligationEvidence",),
        dependencies=(
            "rotation.tank.taunt_application_obligation",
            "rotation.tank.taunt_maintenance_obligation",
            "rotation.tank.defensive_response_obligation",
        ),
        responsibilities=("rotation_tank_canonical_hard_obligation_composition",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "No scalar Tank score is invented. Any resolved hard failure dominates unresolved "
            "evidence; otherwise unresolved remains unresolved, and only candidates passing every "
            "supplied Tank responsibility receive a resolved pass."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.defensive_candidate_claim",
        domain="rotation",
        purpose=(
            "Preserve already-satisfied tank defensive obligations or insert exact caller-"
            "owned block/dodge action claims without choosing timing or displacing occupied "
            "rotation slots."
        ),
        implementation_path="services.rotation_tank_defensive_candidate_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankDefensiveObligation",
            "RotationTankDefensiveActionClaim",
        ),
        outputs=("RotationTankDefensiveCandidateProjection",),
        dependencies=("rotation.tank.defensive_response_obligation",),
        responsibilities=("rotation_tank_defensive_candidate_generation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Claims must supply exact action kind, time, sequence, and optional bar. Existing "
            "matching responses are preserved. Conflicting occupied slots, out-of-window "
            "claims, and unsupported response kinds fail closed rather than moving actions."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.defensive_family_projection",
        domain="rotation",
        purpose=(
            "Apply one explicit tank defensive obligation/claim policy to each generated "
            "candidate through the role-neutral family projection hook before evaluation."
        ),
        implementation_path=(
            "services.rotation_tank_defensive_family_projector_service"
        ),
        inputs=(
            "GeneratedRotationCandidate",
            "RotationTankDefensiveObligation",
            "RotationTankDefensiveActionClaim",
            "RotationCandidateFamilyProjector",
        ),
        outputs=("GeneratedRotationCandidate",),
        dependencies=("rotation.tank.defensive_candidate_claim",),
        responsibilities=("rotation_tank_defensive_family_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Resolved candidates preserve/insert exact responses before family evaluation. "
            "Candidate-specific projection failures remain on that plan's unresolved channel "
            "instead of aborting otherwise valid sibling candidates."
        ),
    ),
)


__all__ = ["ROTATION_TANK_SERVICE_DESCRIPTORS"]
