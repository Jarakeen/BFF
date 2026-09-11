from pathlib import Path

from tools.audit_encounter_guide_coverage import (
    EncounterGuideCoverageRow,
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


def test_checked_in_dungeon_scope_is_newest_first_through_fallen_banners():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = build_coverage_rows(data_root, scope="dungeon")

    assert len(rows) == 12
    assert {(row.release_year, row.release_update) for row in rows} == {
        (2025, 47),
        (2025, 45),
    }
    assert (rows[0].release_year, rows[0].release_update) == (2025, 47)
    assert (rows[-1].release_year, rows[-1].release_update) == (2025, 45)
    assert {row.content_name for row in rows} == {
        "Black Gem Foundry",
        "Naj-Caldeesh",
        "Exiled Redoubt",
        "Lep Seclusa",
    }
    assert {row.encounter_id for row in rows} == {
        "poxito",
        "voskrona_stonehulk_poxito",
        "talen_lah",
        "quarrymaster_saldezaar",
        "black_gem_monstrosity",
        "high_soulbinder_vykand",
        "executioner_jerensi",
        "prime_sorcerer_vandorallen",
        "squall_of_retribution",
        "garvin_the_tracker",
        "noriwen",
        "orpheon_the_tactician",
    }
