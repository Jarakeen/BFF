from services.service_catalog import (
    EvidenceClass,
    canonical_service_for,
    get_service,
)


def test_encounter_domain_read_model_uses_structured_mechanics_without_prose_inference():
    service = canonical_service_for("canonical_encounter_domain_read_model")

    assert service is not None
    assert service.service_id == "encounter.domain_read_model"
    assert service.dependencies == ("encounter.repository",)
    assert service.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "structured fields" in service.notes
    assert "prose hints" in service.notes
    assert "remain unresolved" in service.notes


def test_requirement_overlay_does_not_replace_canonical_encounter_truth():
    service = canonical_service_for("explicit_encounter_requirement_overlay")

    assert service is not None
    assert service.service_id == "encounter.requirement_overlay"
    assert service.dependencies == ("encounter.domain_read_model",)
    assert service.evidence_class is EvidenceClass.POLICY
    assert "remains authoritative" in service.notes
    assert "may not collide" in service.notes


def test_provider_candidate_projection_carries_phase10_truth_without_reinferring_builds():
    service = canonical_service_for("encounter_provider_candidate_projection")

    assert service is not None
    assert service.service_id == "encounter.provider.candidate_projection"
    assert service.dependencies == ("build.saved_capability_analysis",)
    assert "Phase 10 is authoritative" in service.notes
    assert "fresh build inference" in service.notes


def test_provider_suitability_is_not_capability_and_cannot_promote_unknowns():
    service = canonical_service_for("encounter_provider_suitability_assessment")

    assert service is not None
    assert service.service_id == "encounter.provider.suitability"
    assert service.dependencies == ("encounter.provider.candidate_projection",)
    assert "Suitability is not capability" in service.notes
    assert "cannot make unresolved or conflicting" in service.notes


def test_provider_assignment_never_uses_roster_order_as_strategy():
    service = canonical_service_for("encounter_provider_assignment")

    assert service is not None
    assert service.service_id == "encounter.provider.assignment"
    assert service.dependencies == (
        "encounter.provider.candidate_projection",
        "encounter.provider.suitability",
    )
    assert "Roster order is never a tie-break" in service.notes
    assert "remain unresolved" in service.notes


def test_responsibility_conflicts_require_explicit_double_duty_evidence():
    service = canonical_service_for("encounter_provider_responsibility_conflict_audit")

    assert service is not None
    assert service.service_id == "encounter.provider.responsibility_audit"
    assert service.dependencies == ("encounter.provider.assignment",)
    assert "multiple provider rows is not itself a conflict" in service.notes
    assert "explicit evidence" in service.notes


def test_encounter_provider_layers_remain_distinct_capabilities():
    ids = {
        get_service("encounter.provider.candidate_projection").service_id,
        get_service("encounter.provider.suitability").service_id,
        get_service("encounter.provider.assignment").service_id,
        get_service("encounter.provider.responsibility_audit").service_id,
    }

    assert ids == {
        "encounter.provider.candidate_projection",
        "encounter.provider.suitability",
        "encounter.provider.assignment",
        "encounter.provider.responsibility_audit",
    }
