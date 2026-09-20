from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


RAID_PLAN_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="raid_plan.repository",
        domain="raid_plan",
        purpose=(
            "Persist and retrieve versioned RaidPlan snapshots without taking ownership "
            "of global Personnel, Character, Saved Build, Team, or encounter identity."
        ),
        implementation_path="services.raid_plan_repository",
        inputs=("RaidPlan", "RaidPlanId"),
        outputs=("PersistedRaidPlan", "RaidPlanCollection"),
        responsibilities=("raid_plan_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "The repository stores trial-specific planning snapshots only. Runtime state, "
            "ESO Logs evidence, and optimization state are not persistence dependencies."
        ),
    ),
    ServiceDescriptor(
        service_id="raid.readiness.evidence",
        domain="raid_plan",
        purpose="Compose per-chair Readiness build and Coverage state from persisted Raid Plan, canonical build identity, and the existing plan-scoped Coverage evidence pipeline.",
        implementation_path="services.raid_readiness_evidence_service",
        inputs=("RaidPlan", "CanonicalBuildCatalog", "RaidCoverageSnapshot"),
        outputs=("RaidReadinessEvidence",),
        dependencies=(
            "build.catalog.persistence",
            "coverage.raid_plan.scope",
        ),
        responsibilities=(
            "raid_readiness_build_state_projection",
            "raid_readiness_coverage_state_projection",
        ),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Readiness does not infer Rotation, Sustain, proc uptime, or telemetry. Selected builds must resolve canonically; partial Comp planning remains visibly Planned; Coverage reuses saved-build/planned-gear/planned-skill and assignment evidence.",
    ),
    ServiceDescriptor(
        service_id="coverage.named_group_effect_projection",
        domain="coverage",
        purpose=(
            "Project exact canonical EffectVariant identities from saved-build audits into the raid-facing "
            "buff/debuff catalog without aliases, self-only promotion, or uptime inference."
        ),
        implementation_path="services.raid_named_group_effect_capability_service",
        inputs=("RaidCoverageSnapshot", "PlayerBuild", "SavedBuildCapabilityAudit"),
        outputs=("RaidCoverageSnapshot",),
        dependencies=("build.saved_capability_analysis",),
        responsibilities=("raid_named_group_effect_static_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Only exact canonical identity matches are projected. Effects classified as self-only or with unknown target "
            "scope fail closed; conditional/triggered effects never claim uptime."
        ),
    ),
    ServiceDescriptor(
        service_id="raid_plan.coverage_scope",
        domain="raid_plan",
        purpose=(
            "Resolve one RaidPlan into exact selected saved builds plus explicit Primary/Secondary "
            "coverage-assignment labels for static Coverage inspection."
        ),
        implementation_path="services.raid_plan_coverage_scope_service",
        inputs=("RaidPlan", "PlayerBuild", "CoverageEffectName"),
        outputs=("RaidPlanCoverageScope",),
        responsibilities=("raid_plan_coverage_scope_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Saved-build resolution fails closed. Assignment labels are planning intent only; "
            "exact label matches may populate provider/backup presentation but never prove effect availability or uptime."
        ),
    ),
    ServiceDescriptor(
        service_id="raid_plan.optimizer_adviser",
        domain="raid_plan",
        purpose=(
            "Review one explicit RaidPlan against exact saved-build and Coverage evidence and return "
            "explainable advisory findings without applying team, build, assignment, or runtime changes."
        ),
        implementation_path="services.raid_plan_optimizer_adviser_service",
        inputs=("RaidPlan", "PlayerBuild", "SavedBuildCapabilityAudit", "RaidCoverageSnapshot"),
        outputs=("RaidPlanAdviserReview", "RaidPlanAdviserFinding"),
        dependencies=("raid_plan.coverage_scope", "build.saved_capability_analysis"),
        responsibilities=("raid_plan_read_only_optimization_advice",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Adviser findings distinguish plan blockers, coverage gaps, conditional execution, provider redundancy, "
            "and Foundry evidence debt. Recommendations are read-only and never mutate RaidPlan or saved builds."
        ),
    ),
)


__all__ = ["RAID_PLAN_SERVICE_DESCRIPTORS"]
