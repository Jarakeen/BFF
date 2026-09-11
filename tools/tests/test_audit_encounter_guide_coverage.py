from tools.audit_encounter_guide_coverage import EncounterGuideCoverageRow, _line


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
