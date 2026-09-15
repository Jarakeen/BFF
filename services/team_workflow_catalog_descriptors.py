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
        service_id="team.roster.player_identity",
        domain="team",
        purpose="Persist explicit player aliases and merge two user-confirmed Personnel identities without guessing equivalence.",
        implementation_path="services.roster_player_identity_service",
        inputs=("EsoDatabase", "RosterMember", "BuildCatalog", "ExplicitPlayerMergeDecision"),
        outputs=("PlayerAlias", "PlayerIdentityMergeResult"),
        dependencies=("team.roster.persistence", "build.catalog.persistence"),
        responsibilities=("roster_player_alias_history", "roster_player_identity_merge"),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "Aliases are exact user-owned identity evidence learned only from explicit merge/rename/manual entry. "
            "The service never infers that unrelated names belong to the same human."
        ),
    ),
    ServiceDescriptor(
        service_id="team.roster.canonical_player_binding",
        domain="team",
        purpose="Bind Personnel rows to explicit stable Build Catalog player identity without name inference.",
        implementation_path="services.roster_canonical_player_binding_service",
        inputs=("EsoDatabase", "BuildService", "roster_member_id", "canonical_player_id"),
        outputs=("CanonicalPlayerBinding",),
        dependencies=("team.roster.persistence", "build.catalog.persistence"),
        responsibilities=("roster_canonical_player_binding",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "Bindings are explicit. Multiple current player+character Personnel rows may reference the same canonical player. "
            "If a canonical character is already bound, its Build Catalog player owner must match. No name inference is permitted."
        ),
    ),
    ServiceDescriptor(
        service_id="team.roster.canonical_character_binding",
        domain="team",
        purpose="Bind one Personnel row to one explicit stable Build Catalog character identity and preserve its canonical player owner.",
        implementation_path="services.roster_canonical_character_binding_service",
        inputs=("EsoDatabase", "BuildService", "roster_member_id", "canonical_character_id"),
        outputs=("CanonicalCharacterBinding",),
        dependencies=(
            "team.roster.persistence",
            "team.roster.canonical_player_binding",
            "build.catalog.persistence",
        ),
        responsibilities=("roster_canonical_character_binding",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "Character binding is one-to-one at the Personnel-row layer. The supplied character_id must exist; its player owner is "
            "derived from canonical Build Catalog identity, duplicate character ownership fails closed, and names are never used as identity proof."
        ),
    ),
    ServiceDescriptor(
        service_id="team.generated_draft.persistence",
        domain="team",
        purpose="Persist Comp Maker composition, recruitment, and candidate evidence as a draft awaiting explicit adoption.",
        implementation_path="services.generated_roster_draft_service",
        inputs=("EsoDatabase", "GeneratedRosterDraftSlot"),
        outputs=("GeneratedRosterDraft",),
        dependencies=("team.roster.persistence",),
        responsibilities=("generated_roster_draft_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Generated draft storage is canonical and not authoritative RaidPlan state. "
            "Legacy generated_roster_plan tables are migration input only. "
            "Open recruit chairs remain requirements rather than invented players; explicit adoption owns final Team/RaidPlan selections."
        ),
    ),
    ServiceDescriptor(
        service_id="compat.generated_roster_plan.imports",
        domain="compatibility",
        purpose="Preserve old generated-roster-plan import paths while live callers migrate to canonical generated draft APIs.",
        implementation_path="services.generated_roster_plan_service",
        inputs=("legacy import path",),
        outputs=("GeneratedRosterDraft", "GeneratedRosterDraftService", "GeneratedRosterDraftSlot"),
        dependencies=("team.generated_draft.persistence",),
        responsibilities=("generated_roster_plan_import_compatibility",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "Compatibility-only wrapper. It owns no persistence or RaidPlan state and must not gain new runtime behavior. "
            "Normal runtime callers should migrate to services.generated_roster_draft_service."
        ),
    ),
    ServiceDescriptor(
        service_id="team.generated_draft.prescription_persistence",
        domain="team",
        purpose="Persist preserved recruit-prescription evidence against canonical generated-draft identities.",
        implementation_path="services.generated_roster_draft_prescription_service",
        inputs=("EsoDatabase", "draft_id", "slot_name", "RecruitPrescriptionEvidence"),
        outputs=("RecruitPrescriptionEvidence",),
        dependencies=("team.generated_draft.persistence",),
        responsibilities=("generated_roster_draft_prescription_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Canonical prescription rows reference generated_roster_draft ids. "
            "Legacy generated_roster_recruit_prescription rows are read-migration input only and are never rewritten."
        ),
    ),
    ServiceDescriptor(
        service_id="team.roster.recruit_adoption",
        domain="team",
        purpose="Attach a real roster member and saved build to an open generated-draft chair while preserving the original recruit prescription as evidence.",
        implementation_path="services.roster_recruit_adoption_service",
        inputs=("GeneratedRosterDraft", "RosterMember", "PlayerBuild"),
        outputs=("GeneratedRosterDraft",),
        dependencies=(
            "team.generated_draft.persistence",
            "team.generated_draft.prescription_persistence",
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
        implementation_path="migration.phase12_5_legacy_plan_repair",
        inputs=("GeneratedRosterDraft", "BuildRoster", "RosterMember"),
        outputs=("Phase125LegacyPlanRepair", "GeneratedRosterDraft"),
        dependencies=("team.generated_draft.persistence", "team.roster.persistence"),
        responsibilities=("phase12_5_legacy_plan_repair",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes="Migration-only compatibility repair. It may promote only uniquely provable saved assignments; ambiguous or external evidence remains explicit and is never converted into a current team recommendation.",
    ),
    ServiceDescriptor(
        service_id="audit.phase12_5.team_workflow",
        domain="audit",
        purpose="Audit persisted Phase 12.5 generated-draft/team identity integrity without changing data or claiming encounter performance.",
        implementation_path="migration.phase12_5_team_workflow_audit",
        inputs=("GeneratedRosterDraft", "BuildRoster", "RosterMember", "RecruitPrescriptionEvidence"),
        outputs=("Phase125TeamWorkflowAudit",),
        dependencies=("team.generated_draft.persistence", "team.roster.persistence"),
        responsibilities=("phase12_5_team_workflow_audit",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="Read-only migration-era integrity audit. Recruit/open chairs and unresolved encounter-facing details are boundaries, not failures; encounter compliance and raid outcome remain later-phase responsibilities.",
    ),
    *BUILD_SERVICE_DESCRIPTORS,
    *FOUNDATION_SERVICE_DESCRIPTORS,
)


__all__ = ["TEAM_WORKFLOW_SERVICE_DESCRIPTORS"]
