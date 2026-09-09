from services.service_catalog import (
    EvidenceClass,
    canonical_service_for,
)


def test_boss_source_projection_stops_at_reviewable_evidence():
    service = canonical_service_for("encounter_boss_source_evidence_projection")

    assert service is not None
    assert service.service_id == "encounter.boss_source.evidence_projection"
    assert service.evidence_class is EvidenceClass.OBSERVATIONAL
    assert "evidence, not canonical truth" in service.notes
    assert "stops before canonical persistence" in service.notes
    assert "inferred and incomplete" in service.notes


def test_mechanics_coverage_audit_is_readiness_metadata_not_mechanics_truth():
    service = canonical_service_for("canonical_mechanics_coverage_audit")

    assert service is not None
    assert service.service_id == "mechanics.coverage.audit"
    assert service.evidence_class is EvidenceClass.MIXED
    assert "not ESO mechanics itself" in service.notes


def test_mechanics_coverage_blocks_only_declared_dependent_decisions():
    service = canonical_service_for("canonical_mechanics_coverage_audit")

    assert service is not None
    assert "MISSING_CRITICAL gaps block only dependent decisions" in service.notes
    assert "fails closed" in service.notes
    assert "without globally disabling unrelated consumers" in service.notes
