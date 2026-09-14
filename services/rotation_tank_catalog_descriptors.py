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
            "application count, and optional bar. Canonical TAUNT utility proves only that "
            "the scheduled skill applies taunt. It does not prove taunt duration, continuous "
            "uptime, target ownership, immunity/overtaunt behavior, or survivability."
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
        ),
        outputs=("RotationTankTauntCandidateProjection",),
        dependencies=("rotation.tank.taunt_application_obligation",),
        responsibilities=("rotation_tank_taunt_candidate_generation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "The requirement owns the exact source skill and application window; the claim owns "
            "only action kind, exact time, sequence, and optional bar. Existing legal applications "
            "are preserved. New casts require saved-build structural evidence proving the exact "
            "skill/Ultimate is slotted on the selected bar; a two-bar source without an explicit "
            "bar remains unresolved. Conflicting slots and missing applications fail closed. "
            "This remains application-only and does not imply duration, maintenance, target "
            "ownership, or overtaunt."
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
            "Saved-build slot evidence is carried through unchanged. Candidate-specific projection "
            "failures remain on that plan's unresolved channel instead of aborting otherwise valid "
            "sibling candidates."
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
