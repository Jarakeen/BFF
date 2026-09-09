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


def test_stickerbook_bookmarks_are_intent_not_ownership_or_optimization_evidence():
    service = canonical_service_for("stickerbook_bookmark_persistence")

    assert service is not None
    assert service.service_id == "stickerbook.bookmarks"
    assert service.dependencies == ("stickerbook.progress",)
    assert service.evidence_class is EvidenceClass.NONE
    assert "user intent only" in service.notes
    assert "do not prove set ownership" in service.notes
    assert "optimization value" in service.notes


def test_motif_recipe_and_lorebook_progress_keep_reference_and_profile_state_separate():
    motif = canonical_service_for("learned_motif_progress")
    recipe = canonical_service_for("learned_recipe_progress")
    lorebook = canonical_service_for("lorebook_progress")

    assert motif is not None
    assert recipe is not None
    assert lorebook is not None
    assert motif.evidence_class is EvidenceClass.MIXED
    assert recipe.evidence_class is EvidenceClass.MIXED
    assert lorebook.evidence_class is EvidenceClass.MIXED
    assert "profile-owned progress" in motif.notes
    assert "user-owned progress" in recipe.notes
    assert "profile-owned progress" in lorebook.notes


def test_learned_collection_services_remain_distinct_capabilities():
    ids = {
        get_service("collectible.motif.progress").service_id,
        get_service("collectible.recipe.progress").service_id,
        get_service("collectible.lorebook.progress").service_id,
    }

    assert ids == {
        "collectible.motif.progress",
        "collectible.recipe.progress",
        "collectible.lorebook.progress",
    }


def test_local_achievement_workbook_is_import_adapter_not_progress_authority():
    service = canonical_service_for("local_achievement_workbook_import")

    assert service is not None
    assert service.service_id == "achievement.workbook.local_import"
    assert service.evidence_class is EvidenceClass.NONE
    assert "does not become the achievement completion authority" in service.notes
    assert "achievement.progress.persistence" in service.notes


def test_local_collectible_workbook_keeps_other_progress_domains_out_of_scope():
    service = canonical_service_for("local_collectible_workbook_import")

    assert service is not None
    assert service.service_id == "collectible.workbook.local_import"
    assert "Motifs, recipes, titles, antiquities, stickerbook" in service.notes
    assert "own progress systems" in service.notes


def test_local_motif_workbook_preserves_historical_whole_row_semantics():
    service = canonical_service_for("local_motif_workbook_import")

    assert service is not None
    assert service.service_id == "collectible.motif.workbook_import"
    assert "whole-motif row level" in service.notes
    assert "not silently reinterpreted" in service.notes


def test_google_sheets_sync_is_external_surface_not_local_progress_authority():
    service = canonical_service_for("google_sheets_achievement_sync")

    assert service is not None
    assert service.service_id == "achievement.google_sheets.sync"
    assert service.evidence_class is EvidenceClass.NONE
    assert "external synchronization surface" in service.notes
    assert "not BFF's local completion authority" in service.notes
    assert "remain explicit" in service.notes
