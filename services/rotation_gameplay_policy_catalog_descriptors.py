from __future__ import annotations

"""Service-catalog metadata for Rotation Builder policy responsibilities."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.encounter_demand_policy.registry",
        domain="rotation",
        purpose=(
            "Load reviewed clock-timed and health-threshold encounter-demand policy "
            "from the persisted Rotation Builder registry without inferring strategy "
            "from encounter prose or names."
        ),
        implementation_path="services.rotation_encounter_demand_policy_registry_service",
        inputs=("EncounterId", "PersistedRotationEncounterDemandPolicyRegistry"),
        outputs=("RotationEncounterDemandPolicyRegistryEntry",),
        responsibilities=("rotation_encounter_demand_policy_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "A missing encounter key means reviewed policy is unavailable; explicitly "
            "empty clock and threshold policy lists mean review resolved that scope to no "
            "demands. Threshold policy still requires explicit difficulty and raid-damage "
            "trajectory before it can become a clock window."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.gameplay_policy.dd_personal_heal",
        domain="rotation",
        purpose=(
            "Assess organized-endgame DD redundant personal-heal slot practice from "
            "the shared gameplay-policy registry without rewriting ESO mechanics."
        ),
        implementation_path="services.rotation_gameplay_policy_assessment_service",
        inputs=("RotationGameplayPolicyContext", "GameplayPolicy"),
        outputs=("RotationGameplayPolicyAssessment",),
        responsibilities=("rotation_gameplay_policy_assessment",),
        roles=("DPS",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Consumes shared endgame gameplay policy and explicit encounter/assignment "
            "exceptions. It does not infer healing identity from skill names or tooltips."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.gameplay_policy.personal_heal_slot_context",
        domain="rotation",
        purpose=(
            "Project canonical saved-build skill component recipient evidence into "
            "candidate gameplay-policy context without classifying skills by name."
        ),
        implementation_path="services.rotation_candidate_gameplay_policy_context_service",
        inputs=(
            "PlayerBuild",
            "SavedBuildSkillTooltipService",
            "GeneratedRotationCandidate",
        ),
        outputs=("RotationGameplayPolicyContext",),
        dependencies=("rotation.gameplay_policy.dd_personal_heal",),
        responsibilities=("rotation_gameplay_policy_context_projection",),
        roles=("DPS",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Skill identity and HEAL recipient scope come from canonical component data; "
            "healer reliability and encounter exceptions remain explicit policy inputs."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.gameplay_policy.final_recovery_role_evidence",
        domain="rotation",
        purpose=(
            "Compose final stabilized recovery replay, canonical role evidence, final "
            "scorecard evidence, and optional gameplay-practice context into the "
            "role-aware ranking input used before final selection."
        ),
        implementation_path="services.rotation_recovery_final_role_evidence_service",
        inputs=(
            "RecoveryHeavyStabilizedCandidateSnapshot",
            "RotationCandidatePlanEvidence",
            "RotationGameplayPolicyContext",
            "RotationCandidateScorecard",
        ),
        outputs=("RotationRoleAwareRankingInput",),
        dependencies=(
            "rotation.gameplay_policy.dd_personal_heal",
            "rotation.gameplay_policy.personal_heal_slot_context",
        ),
        responsibilities=("rotation_final_recovery_role_evidence_composition",),
        roles=("DPS", "Healer", "Tank", "Support"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses the stabilized replay as sustain-margin authority and delegates role "
            "output/support/hard-obligation mechanics to existing canonical providers."
        ),
    ),
)


__all__ = ["ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS"]
