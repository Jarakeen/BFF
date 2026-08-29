from __future__ import annotations

from minmax.source_provenance import load_source_provenance


def test_skill_coefficient_source_keeps_unknown_version_fields_explicit():
    source = load_source_provenance("skill_coefficients")

    assert source.source_system == "UESP ESO Log Collector"
    assert source.source_kind == "derived_virtual_view_export"
    assert source.export_url == (
        "https://esolog.uesp.net/exportJson.php?table=skillCoef"
    )
    assert source.export_table == "skillCoef"
    assert source.record_count == 3629
    assert source.retrieved_at is None
    assert source.game_update is None
    assert source.api_version is None
    assert source.provenance_status == "incomplete"
    assert "minedSkills tooltip observations" in source.derivation
