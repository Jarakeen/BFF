from __future__ import annotations

from services.service_catalog import (
    EvidenceClass,
    SERVICE_CATALOG,
    canonical_service_for,
)


def test_roster_and_generated_draft_persistence_have_distinct_ownership() -> None:
    roster = canonical_service_for("roster_persistence")
    drafts = canonical_service_for("generated_roster_draft_persistence")

    assert roster is not None
    assert drafts is not None
    assert roster.service_id == "team.roster.persistence"
    assert drafts.service_id == "team.generated_draft.persistence"
    assert roster.service_id in drafts.dependencies
    assert "must not fabricate roster members" in roster.notes
    assert "not authoritative RaidPlan state" in drafts.notes
    assert "Open recruit chairs" in drafts.notes


def test_recruit_adoption_preserves_prescription_without_inventing_build_detail() -> None:
    adoption = canonical_service_for("roster_recruit_adoption")

    assert adoption is not None
    assert adoption.service_id == "team.roster.recruit_adoption"
    assert adoption.evidence_class is EvidenceClass.MIXED
    assert "team.generated_draft.persistence" in adoption.dependencies
    assert "team.prescription.slot_constraints" in adoption.dependencies
    assert "does not invent exact gear slots" in adoption.notes


def test_phase12_5_repair_is_migration_only_and_audit_is_read_only() -> None:
    repair = canonical_service_for("phase12_5_legacy_plan_repair")
    audit = canonical_service_for("phase12_5_team_workflow_audit")

    assert repair is not None
    assert audit is not None
    assert repair.domain == "migration"
    assert audit.domain == "audit"
    assert repair.implementation_path == "migration.phase12_5_legacy_plan_repair"
    assert audit.implementation_path == "migration.phase12_5_team_workflow_audit"
    assert "GeneratedRosterDraft" in repair.inputs
    assert "GeneratedRosterDraft" in repair.outputs
    assert "Migration-only" in repair.notes
    assert "uniquely provable" in repair.notes
    assert "Read-only" in audit.notes
    assert "raid outcome remain later-phase responsibilities" in audit.notes


def test_phase12_5_workflow_services_do_not_claim_team_optimization_responsibility() -> None:
    workflow_ids = {
        "team.roster.persistence",
        "team.generated_draft.persistence",
        "team.roster.recruit_adoption",
        "migration.phase12_5.legacy_plan_repair",
        "audit.phase12_5.team_workflow",
    }

    for service_id in workflow_ids:
        descriptor = SERVICE_CATALOG.get(service_id)
        assert descriptor is not None
        assert "team_optimization" not in " ".join(descriptor.responsibilities)
        assert "comp_builder_whole_team_candidate_optimization" not in descriptor.responsibilities
