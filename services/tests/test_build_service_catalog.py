from __future__ import annotations

from services.service_catalog import (
    EvidenceClass,
    SERVICE_CATALOG,
    ServiceAuthority,
    canonical_service_for,
)


def test_build_catalog_owns_canonical_character_build_persistence() -> None:
    descriptor = canonical_service_for("canonical_character_build_persistence")

    assert descriptor is not None
    assert descriptor.service_id == "build.catalog.persistence"
    assert descriptor.implementation_path == "services.build_catalog_service"
    assert "source of truth" in descriptor.notes


def test_build_service_is_compatibility_facade_not_canonical_storage_owner() -> None:
    facade = canonical_service_for("build_roster_compatibility_persistence")

    assert facade is not None
    assert facade.service_id == "build.compatibility.persistence_facade"
    assert "build.catalog.persistence" in facade.dependencies
    assert "Compatibility/UI facade only" in facade.notes


def test_old_canonical_build_service_is_explicitly_deprecated() -> None:
    legacy = SERVICE_CATALOG.get("build.legacy.canonical_persistence_v1")

    assert legacy is not None
    assert legacy.authority is ServiceAuthority.DEPRECATED
    assert legacy.superseded_by == "build.catalog.persistence"
    assert "No current repository consumers were found" in legacy.notes


def test_build_screenshot_intake_stays_observational_and_review_first() -> None:
    staging = canonical_service_for("build_screenshot_evidence_staging")

    assert staging is not None
    assert staging.evidence_class is EvidenceClass.OBSERVATIONAL
    assert staging.ui_safe is True
    assert "does not write canonical build fields automatically" in staging.notes


def test_saved_build_capability_analysis_does_not_claim_runtime_uptime() -> None:
    analysis = canonical_service_for("saved_build_static_capability_analysis")

    assert analysis is not None
    assert analysis.service_id == "build.saved_capability_analysis"
    assert analysis.evidence_class is EvidenceClass.GAME_MECHANIC
    assert analysis.encounter_aware is False
    assert "Static capability availability is not runtime uptime" in analysis.notes
