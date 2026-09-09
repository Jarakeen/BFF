from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    canonical_service_for,
    get_service,
)


def test_live_reference_lookup_uses_sqlite_and_keeps_watch_suggestions_noncanonical():
    service = canonical_service_for("canonical_eso_reference_ui_lookup")

    assert service is not None
    assert service.service_id == "reference.eso_db.ui_lookup"
    assert service.ui_safe is True
    assert service.evidence_class is EvidenceClass.MIXED
    assert "convenience heuristics" in service.notes
    assert "canonical mechanic truth" in service.notes


def test_legacy_json_reference_library_is_deprecated_with_sqlite_successor():
    service = get_service("reference.legacy_json_library")

    assert service is not None
    assert service.authority is ServiceAuthority.DEPRECATED
    assert service.superseded_by == "reference.eso_db.ui_lookup"
    assert "old_pages" in service.notes


def test_sqlite_achievement_reference_is_canonical_reference_not_user_progress():
    service = canonical_service_for("canonical_achievement_reference_lookup")

    assert service is not None
    assert service.service_id == "achievement.reference.sqlite"
    assert service.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "User completion/progress state" in service.notes


def test_legacy_achievement_json_reader_is_deprecated_with_sqlite_successor():
    service = get_service("achievement.reference.legacy_json")

    assert service is not None
    assert service.authority is ServiceAuthority.DEPRECATED
    assert service.superseded_by == "achievement.reference.sqlite"
    assert "old_pages" in service.notes
