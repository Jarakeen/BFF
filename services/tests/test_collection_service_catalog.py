from services.service_catalog import (
    EvidenceClass,
    canonical_service_for,
    get_service,
)


def test_achievement_progress_persistence_owns_local_completion_state():
    service = canonical_service_for("achievement_progress_persistence")

    assert service is not None
    assert service.service_id == "achievement.progress.persistence"
    assert service.evidence_class is EvidenceClass.NONE
    assert service.ui_safe is True
    assert "source of truth for completion checkboxes" in service.notes
    assert "Default" in service.notes


def test_achievement_stats_are_read_only_composition_of_reference_and_progress():
    service = canonical_service_for("achievement_progress_summary")

    assert service is not None
    assert service.service_id == "achievement.stats.summary"
    assert service.dependencies == (
        "achievement.reference.sqlite",
        "achievement.progress.persistence",
    )
    assert service.evidence_class is EvidenceClass.MIXED
    assert "does not alter either source" in service.notes


def test_achievement_export_is_not_an_alternate_progress_authority():
    service = canonical_service_for("achievement_progress_export")

    assert service is not None
    assert service.service_id == "achievement.progress.export"
    assert service.dependencies == (
        "achievement.reference.sqlite",
        "achievement.progress.persistence",
    )
    assert "does not become an alternate progress authority" in service.notes


def test_collectible_profiled_progress_keeps_shared_catalog_separate_from_ownership():
    database = get_service("collectible.database.workspace")
    profiled = canonical_service_for("profiled_collectible_progress")

    assert database is not None
    assert profiled is not None
    assert profiled.service_id == "collectible.profiled_progress"
    assert profiled.dependencies == ("collectible.database.workspace",)
    assert database.evidence_class is EvidenceClass.MIXED
    assert "catalog is shared" in profiled.notes
    assert "ownership/progress is profile-specific" in profiled.notes


def test_stickerbook_repairs_collection_shape_without_mutating_canonical_source_tables():
    service = canonical_service_for("stickerbook_progress_tracking")

    assert service is not None
    assert service.service_id == "stickerbook.progress"
    assert service.evidence_class is EvidenceClass.MIXED
    assert "Crafted sets are intentionally excluded" in service.notes
    assert "do not mutate canonical source tables" in service.notes
