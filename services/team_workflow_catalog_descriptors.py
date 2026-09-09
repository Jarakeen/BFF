from __future__ import annotations

"""Explicit roster/team-workflow catalog descriptors.

Metadata only. These descriptors document ownership and lifecycle boundaries for
Comp Maker / Roster workflow persistence, adoption, migration repair, and audit.
They do not replace typed imports or explicit runtime wiring.
"""

from services.build_catalog_descriptors import BUILD_SERVICE_DESCRIPTORS
from services.foundation_catalog_descriptors import FOUNDATION_SERVICE_DESCRIPTORS
from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


TEAM_WORKFLOW_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="team.roster.persistence",
        domain="team",
        purpose="Persist canonical roster members, durable team identities, membership, and raid schedules.",
        implementation_path="services.roster_service",
        inputs=("EsoDatabase", "RosterMember", "TeamSchedule"),
        outputs=("RosterMember", "RosterTeamIdentity", "TeamSchedule"),
        responsibilities=("roster_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="Roster persistence owns real people and team membership; recruitment-only chairs must not fabricate roster members.",
    ),
    ServiceDescriptor(
        service_id="team.generated_plan.persistence",
        domain="team",
        purpose="Persist generated roster assignments and explicit recruitment requirements under one durable team identity.",
        implementation_path="services.generated_roster_plan_service",
        inputs=("EsoDatabase", "GeneratedRosterPlanSlot"),
        outputs=("GeneratedRosterPlan",),
        dependencies=("team.roster.persistence",),
        responsibilities=("generated_roster_plan_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes="Generated assignments remain separate from roster membership; open recruit chairs are persisted as requirements rather than invented players.",
    ),
    ServiceDescriptor(
        service_id="team.roster.recruit_adoption",
        domain="team",
        purpose="Attach a real roster member and saved build to an open generated-team chair while preserving the original recruit prescription as evidence.",
        implementation_path="services.roster_recruit_adoption_service",
        inputs=("GeneratedRosterPlan", "RosterMember", "PlayerBuild"),
        outputs=("GeneratedRosterPlan",),
        dependencies=(
            "team.generated_plan.persistence",
            "team.roster.persistence",
            "team.prescription.slot_constraints",
        ),
        responsibilities=("roster_recruit_adoption",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Adoption preserves the original prescription separately and does not invent exact gear slots, traits, enchants, or skill-bar placement.",
    ),
    ServiceDescriptor(
        service_id="migration.phase12_5.legacy_plan_repair",
        domain="migration",
        purpose="Repair only provable pre-Phase-12.5 generated-plan identity inconsistencies while preserving ambiguous legacy evidence.",
        implementation_path="services.phase12_5_legacy_plan_repair",
        inputs=("GeneratedRosterPlan", "BuildRoster", "RosterMember"),
        outputs=("Phase125LegacyPlanRepair", "GeneratedRosterPlan"),
        dependencies=("team.generated_plan.persistence", "team.roster.persistence"),
        responsibilities=("phase12_5_legacy_plan_repair",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes="Migration-only ownership repair. It may promote only uniquely provable saved assignments; ambiguous or external evidence remains explicit and is never converted into a current team recommendation.",
    ),
    ServiceDescriptor(
        service_id="audit.phase12_5.team_workflow",
        domain="audit",
        purpose="Audit persisted Phase 12.5 team identity and assignment integrity without changing data or claiming encounter performance.",
        implementation_path="services.phase12_5_team_workflow_audit",
        inputs=("GeneratedRosterPlan", "BuildRoster", "RosterMember", "RecruitPrescriptionEvidence"),
        outputs=("Phase125TeamWorkflowAudit",),
        dependencies=("team.generated_plan.persistence", "team.roster.persistence"),
        responsibilities=("phase12_5_team_workflow_audit",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="Read-only integrity audit. Recruit/open chairs and unresolved encounter-facing details are boundaries, not failures; encounter compliance and raid outcome remain later-phase responsibilities.",
    ),
    *BUILD_SERVICE_DESCRIPTORS,
    *FOUNDATION_SERVICE_DESCRIPTORS,
)


__all__ = ["TEAM_WORKFLOW_SERVICE_DESCRIPTORS"]
