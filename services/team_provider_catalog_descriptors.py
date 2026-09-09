from __future__ import annotations

"""Explicit Team Provider service catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit dependency
wiring; these rows describe ownership, evidence boundaries, and consumer-safe outputs.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


TEAM_PROVIDER_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="team.provider.effect_eligibility",
        domain="team",
        purpose="Measure effect-specific eligible encounter time and covered uptime from explicit semantic windows.",
        implementation_path="services.team_provider_effect_eligibility_service",
        inputs=("TeamProviderEffectEligibilityRule", "EncounterEligibilityWindow", "TeamProviderTimedApplication"),
        outputs=("TeamProviderEligibleUptimeResult",),
        dependencies=("team.provider.temporal_coverage",),
        responsibilities=("team_provider_effect_eligibility",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Eligibility windows and tags are explicit upstream evidence; missing target identity never silently becomes eligible time.",
    ),
    ServiceDescriptor(
        service_id="team.provider.uptime_policy",
        domain="team",
        purpose="Assess observed provider uptime against explicit encounter-scoped strategy targets without treating targets as universal mechanics.",
        implementation_path="services.team_provider_uptime_policy_service",
        inputs=("TeamProviderUptimePolicy", "ObservedUptimeRatio"),
        outputs=("TeamProviderUptimeAssessment",),
        responsibilities=("team_provider_uptime_policy_assessment",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Uptime targets are strategy or benchmark policy and remain separate from theoretical mechanic ceilings.",
    ),
    ServiceDescriptor(
        service_id="team.provider.effect_uptime_assessment",
        domain="team",
        purpose="Bridge effect-purpose eligibility windows into encounter-scoped uptime policy assessment.",
        implementation_path="services.team_provider_effect_uptime_assessment_service",
        inputs=("TeamProviderUptimePolicy", "TeamProviderEffectEligibilityRule", "EncounterEligibilityWindow", "TeamProviderTimedApplication"),
        outputs=("TeamProviderEffectUptimeAssessment",),
        dependencies=("team.provider.effect_eligibility", "team.provider.uptime_policy"),
        responsibilities=("team_provider_effect_uptime_assessment",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Prevents full-fight uptime percentages from being compared to damageable-time or otherwise scoped targets.",
    ),
    ServiceDescriptor(
        service_id="team.provider.marginal_value",
        domain="team",
        purpose="Measure only named effects a provider candidate adds beyond the current team using the shared named-buff stacking model.",
        implementation_path="services.team_provider_marginal_value_service",
        inputs=("NamedBuffContribution",),
        outputs=("TeamProviderMarginalValue",),
        responsibilities=("team_provider_marginal_named_effect_value",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Preserves objective-specific deltas and never collapses unlike ESO objectives into one synthetic score.",
    ),
    ServiceDescriptor(
        service_id="team.provider.workload_policy",
        domain="team",
        purpose="Apply explicit ordered encounter and role priorities among non-dominated provider workload plans.",
        implementation_path="services.team_provider_workload_policy_service",
        inputs=("TeamProviderWorkloadDecisionResult", "TeamProviderWorkloadPolicy"),
        outputs=("TeamProviderWorkloadPolicyResult",),
        dependencies=("team.provider.workload_decision",),
        responsibilities=("team_provider_workload_policy_selection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Policy may choose only among frontier survivors and uses lexicographic priorities instead of invented weighted exchange rates.",
    ),
    ServiceDescriptor(
        service_id="team.provider.workload_explanation",
        domain="team",
        purpose="Render UI-safe coverage, workload, frontier, blocker, and policy facts for Comp Maker and Team Optimization.",
        implementation_path="services.team_provider_workload_explanation_service",
        inputs=("TeamProviderRotationWorkload", "TeamProviderWorkloadCandidateResult", "TeamProviderWorkloadPolicyResult"),
        outputs=("TeamProviderWorkloadExplanation", "TeamProviderWorkloadComparisonExplanation"),
        dependencies=("team.provider.rotation_workload", "team.provider.workload_decision", "team.provider.workload_policy"),
        responsibilities=("team_provider_workload_explanation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Explanations expose separate tradeoffs and policy state without declaring unlike workload dimensions universally equivalent.",
    ),
)


__all__ = ["TEAM_PROVIDER_SERVICE_DESCRIPTORS"]
