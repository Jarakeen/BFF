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
)


__all__ = ["ROTATION_TANK_SERVICE_DESCRIPTORS"]
