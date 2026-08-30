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


def test_provisioning_exports_preserve_record_counts_and_unknown_versions():
    food = load_source_provenance("provisioning_food")
    drink = load_source_provenance("provisioning_drink")

    assert food.export_table == "minedItemSummary"
    assert food.record_count == 492
    assert drink.export_table == "minedItemSummary"
    assert drink.record_count == 518
    assert food.game_update is None
    assert drink.game_update is None
    assert food.provenance_status == "incomplete"
    assert drink.provenance_status == "incomplete"
