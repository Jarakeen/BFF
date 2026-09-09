from __future__ import annotations

from services.service_catalog import (
    EvidenceClass,
    SERVICE_CATALOG,
    canonical_service_for,
)


def test_roster_and_generated_plan_persistence_are_distinct_canonical_owners() -> None:
    roster = canonical_service_for("roster_persistence")
    plans = canonical_service_for("generated_roster_plan_persistence")

    assert roster is not None
    assert plans is not None
    assert roster.service_id == "team.roster.persistence"
    assert plans.service_id == "team.generated_plan.persistence"
    assert roster.service_id in plans.dependencies
    assert "must not fabricate roster members" in roster.notes
    assert "open recruit chairs" in plans.notes


def test_recruit_adoption_preserves_prescription_without_inventing_build_detail() -> None:
    adoption = canonical_service_for("roster_recruit_adoption")

    assert adoption is not None
    assert adoption.service_id == "team.roster.recruit_adoption"
    assert adoption.evidence_class is EvidenceClass.MIXED
    assert "team.generated_plan.persistence" in adoption.dependencies
    assert "team.prescription.slot_constraints" in adoption.dependencies
    assert "does not invent exact gear slots" in adoption.notes


def test_phase12_5_repair_is_migration_only_and_audit_is_read_only() -> None:
    repair = canonical_service_for("phase12_5_legacy_plan_repair")
    audit = canonical_service_for("phase12_5_team_workflow_audit")

    assert repair is not None
    assert audit is not None
    assert repair.domain == "migration"
    assert audit.domain == "audit"
    assert "Migration-only" in repair.notes
    assert "uniquely provable" in repair.notes
    assert "Read-only integrity audit" in audit.notes
    assert "raid outcome remain later-phase responsibilities" in audit.notes


def test_phase12_5_workflow_services_do_not_claim_team_optimization_responsibility() -> None:
    workflow_ids = {
        "team.roster.persistence",
        "team.generated_plan.persistence",
        "team.roster.recruit_adoption",
        "migration.phase12_5.legacy_plan_repair",
        "audit.phase12_5.team_workflow",
    }

    for service_id in workflow_ids:
        descriptor = SERVICE_CATALOG.get(service_id)
        assert descriptor is not None
        assert "team_optimization" not in " ".join(descriptor.responsibilities)
        assert "comp_builder_whole_team_candidate_optimization" not in descriptor.responsibilities
