from pathlib import Path

from services.encounter_boss_guide import EncounterBossGuideService
from tools.audit_encounter_guide_coverage import (
    EncounterGuideCoverageRow,
    _canonical_phase_count,
    _content_key,
    _include_content,
    _line,
    _parse_args,
    build_coverage_rows,
)


def test_coverage_row_prefers_canonical_timeline_when_present():
    row = EncounterGuideCoverageRow(
        encounter_id="boss",
        content_name="Trial",
        encounter_name="Boss",
        canonical_timeline_rows=3,
        reviewed_timeline_rows=5,
        strategy_rows=4,
    )

    assert row.effective_timeline_source == "canonical"
    assert row.timeline_missing is False
    assert row.strategy_missing is False


def test_coverage_row_uses_reviewed_fallback_when_canonical_timeline_is_missing():
    row = EncounterGuideCoverageRow(
        encounter_id="boss",
        content_name="Trial",
        encounter_name="Boss",
        canonical_timeline_rows=0,
        reviewed_timeline_rows=2,
        strategy_rows=1,
    )

    assert row.effective_timeline_source == "reviewed_fallback"
    assert row.timeline_missing is False
    assert row.strategy_missing is False


def test_coverage_row_uses_reviewed_fallback_when_canonical_persistence_is_unavailable():
    row = EncounterGuideCoverageRow(
        encounter_id="boss",
        content_name="Dungeon",
        encounter_name="Boss",
        canonical_timeline_rows=None,
        reviewed_timeline_rows=2,
        strategy_rows=1,
    )

    text = _line(row)
    assert row.effective_timeline_source == "reviewed_fallback"
    assert row.timeline_missing is False
    assert "canonical=unavailable" in text


def test_canonical_phase_count_marks_missing_database_unavailable(tmp_path: Path):
    service = EncounterBossGuideService(tmp_path / "missing.db")
    assert _canonical_phase_count(service, ("boss",)) is None


def test_coverage_row_reports_missing_timeline_and_strategy():
    row = EncounterGuideCoverageRow(
        encounter_id="boss",
        content_name="Trial",
        encounter_name="Boss",
        canonical_timeline_rows=0,
        reviewed_timeline_rows=0,
        strategy_rows=0,
    )
    text = _line(row)
    assert row.timeline_missing is True
    assert row.strategy_missing is True
    assert "MISSING TIMELINE" in text
    assert "MISSING STRATEGY" in text


def test_trial_scope_reuses_known_trial_names_and_normalizes_leading_the():
    assert _content_key("The Halls of Fabrication") == "halls of fabrication"
    assert _include_content("Halls of Fabrication", trials_only=True) is True
    assert _include_content("Dreadsail Reef", trials_only=True) is True
    assert _include_content("Arx Corinium", trials_only=True) is False


def test_all_content_scope_keeps_non_trial_content():
    assert _include_content("Arx Corinium", trials_only=False) is True


def test_audit_defaults_to_reviewed_raid_scope():
    args = _parse_args([])
    assert args.dungeons is False
    assert args.raw_trial_records is False
    assert args.all_content is False


def test_audit_scope_flags_are_mutually_distinct():
    dungeon_args = _parse_args(["--dungeons"])
    trial_args = _parse_args(["--raw-trial-records"])
    all_args = _parse_args(["--all-content"])

    assert dungeon_args.dungeons is True
    assert dungeon_args.raw_trial_records is False
    assert dungeon_args.all_content is False
    assert trial_args.dungeons is False
    assert trial_args.raw_trial_records is True
    assert trial_args.all_content is False
    assert all_args.dungeons is False
    assert all_args.raw_trial_records is False
    assert all_args.all_content is True


def test_checked_in_dungeon_scope_is_newest_first_through_ascending_tide():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = build_coverage_rows(data_root, scope="dungeon")

    assert len(rows) == 36
    assert {(row.release_year, row.release_update) for row in rows} == {
        (2025, 47), (2025, 45), (2024, 41), (2023, 37), (2022, 35), (2022, 33)
    }
    assert (rows[0].release_year, rows[0].release_update) == (2025, 47)
    assert (rows[-1].release_year, rows[-1].release_update) == (2022, 33)

    assert {row.content_name for row in rows} == {
        "Black Gem Foundry", "Naj-Caldeesh", "Exiled Redoubt", "Lep Seclusa",
        "Oathsworn Pit", "Bedlam Veil", "Bal Sunnar", "Scrivener's Hall",
        "Earthen Root Enclave", "Graven Deep", "Coral Aerie", "Shipwright's Regret",
    }

    assert {row.encounter_id for row in rows} == {
        "poxito", "voskrona_stonehulk_poxito", "talen_lah",
        "quarrymaster_saldezaar", "black_gem_monstrosity", "high_soulbinder_vykand",
        "executioner_jerensi", "prime_sorcerer_vandorallen", "squall_of_retribution",
        "garvin_the_tracker", "noriwen", "orpheon_the_tactician",
        "packmaster_rethelros", "anthelmir_s_construct", "aradros_the_awakened",
        "shattered_champion", "darkshard", "the_blind",
        "kovan_giryon", "roksa_the_warped", "matriarch_lladi_telvanni",
        "riftmaster_naqri", "ozezan_the_inferno", "valinna",
        "corruption_of_stone", "corruption_of_root", "archdruid_devyric",
        "the_euphotic_gatekeeper", "varzunon", "zelvraak_the_unbreathing",
        "maligalig", "sarydil", "varallion",
        "foreman_bradiggan", "nazaray", "captain_numirril",
    }
