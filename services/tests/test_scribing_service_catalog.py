from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    canonical_service_for,
    get_service,
)


def test_result_name_resolution_prefers_verified_client_capture():
    service = canonical_service_for("scribing_verified_result_name_resolution")

    assert service is not None
    assert service.service_id == "scribing.result_name_resolution"
    assert service.evidence_class is EvidenceClass.OBSERVATIONAL
    assert "client capture takes precedence" in service.notes
    assert "fallback evidence only" in service.notes


def test_simulator_compatibility_uses_structured_data_with_static_fallback():
    service = canonical_service_for("scribing_simulator_compatibility_filtering")

    assert service is not None
    assert service.service_id == "scribing.simulator_compatibility"
    assert service.ui_safe is True
    assert "Structured verified simulator data owns current filtering" in service.notes
    assert "static catalog is a compatibility fallback" in service.notes


def test_u51_pts_reference_stays_versioned_and_noncanonical():
    service = get_service("scribing.u51_pts_reference")

    assert service.authority is ServiceAuthority.EXPERIMENTAL
    assert service.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "versioned PTS snapshot" in service.notes
    assert "not a live-version authority" in service.notes
    assert "not an automatic successor" in service.notes


def test_u51_numeric_ability_ids_never_become_canonical_skill_identity():
    service = get_service("scribing.u51_pts_reference")

    assert "Numeric ability ids remain source evidence" in service.notes
    assert "not canonical semantic skill identity" in service.notes


def test_scribing_capabilities_remain_distinct():
    ids = {
        get_service("scribing.result_name_resolution").service_id,
        get_service("scribing.simulator_compatibility").service_id,
        get_service("scribing.u51_pts_reference").service_id,
    }

    assert ids == {
        "scribing.result_name_resolution",
        "scribing.simulator_compatibility",
        "scribing.u51_pts_reference",
    }
