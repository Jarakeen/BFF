from tools.audit_encounter_guide_coverage import (
    EncounterGuideCoverageRow,
    _content_key,
    _include_content,
    _line,
    _parse_args,
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
    assert args.raw_trial_records is False
    assert args.all_content is False


def test_audit_raw_scope_flags_are_mutually_distinct():
    trial_args = _parse_args(["--raw-trial-records"])
    all_args = _parse_args(["--all-content"])

    assert trial_args.raw_trial_records is True
    assert trial_args.all_content is False
    assert all_args.raw_trial_records is False
    assert all_args.all_content is True
