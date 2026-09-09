from services.service_catalog import (
    EvidenceClass,
    canonical_service_for,
    get_service,
)


def test_esologs_capability_uptime_is_observational_not_static_build_capability():
    service = canonical_service_for("esologs_capability_uptime_analysis")

    assert service is not None
    assert service.service_id == "logs.capability.uptime_analysis"
    assert service.evidence_class is EvidenceClass.OBSERVATIONAL
    assert service.encounter_aware is True
    assert "observed fight uptime" in service.notes
    assert "saved-build static capability" in service.notes


def test_character_progression_preserves_unknown_vs_explicit_zero_boundary():
    service = canonical_service_for("character_progression_persistence")

    assert service is not None
    assert service.service_id == "character.progression.persistence"
    assert service.dependencies == ("build.catalog.persistence",)
    assert service.ui_safe is True
    assert "explicit zero" in service.notes
    assert "unknown/unrecorded" in service.notes


def test_named_buff_resolution_is_shared_canonical_game_mechanic():
    service = canonical_service_for("canonical_named_buff_stacking_resolution")

    assert service is not None
    assert service.service_id == "mechanics.named_buff_resolution"
    assert service.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "Duplicate copies" in service.notes
    assert "Major and Minor" in service.notes


def test_foundation_services_have_distinct_responsibilities():
    ids = {
        get_service("logs.capability.uptime_analysis").service_id,
        get_service("character.progression.persistence").service_id,
        get_service("mechanics.named_buff_resolution").service_id,
    }

    assert ids == {
        "logs.capability.uptime_analysis",
        "character.progression.persistence",
        "mechanics.named_buff_resolution",
    }
