from pathlib import Path


def test_coverage_page_uses_raid_review_tab_instead_of_uptime_analysis() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert 'self.tabs.addTab(self._raid_review_tab(), "RAID REVIEW")' in source
    assert '"UPTIME ANALYSIS"' not in source
    assert '"ENCOUNTER NEEDS"' in source


def test_raid_review_workspace_exposes_backend_binding_surfaces() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    expected_surfaces = (
        "raid_review_overview_card",
        "raid_review_priorities_card",
        "raid_review_working_card",
        "raid_review_role_focus_card",
        "raid_review_players_card",
        "raid_review_evidence_card",
    )
    for surface in expected_surfaces:
        assert f"self.{surface}" in source

    assert 'FoundryCard("Top Priorities"' in source
    assert 'FoundryCard("What Is Working"' in source
    assert 'FoundryCard("Role Focus"' in source
    assert 'FoundryCard("Player Review"' in source
    assert 'FoundryCard("Evidence & Unresolved"' in source


def test_raid_review_workspace_binds_completed_result_contract() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "def apply_raid_review_result(self, result, *, extra_unresolved=()) -> None:" in source
    assert 'getattr(result, "synthesis", None)' in source
    assert 'getattr(result, "player_summaries", ())' in source
    assert 'getattr(result, "unresolved", ())' in source
    assert 'getattr(synthesis, "top_priorities", ())' in source
    assert 'getattr(synthesis, "what_is_working", ())' in source
    assert 'getattr(synthesis, "role_focus", ())' in source
    assert "extra_unresolved" in source


def test_raid_review_binding_clears_stale_cards_and_has_explicit_empty_state() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "card.clear()" in source
    assert "No completed Raid Review result is available." in source
    assert "No priorities available." in source
    assert "No stable player summaries are available for this review." in source
    assert "No unresolved evidence was reported for this review." in source


def test_raid_review_workspace_exposes_api_loaded_pull_picker() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "raid_review_report_input" in source
    assert "raid_review_load_fights_button" in source
    assert "raid_review_fights_table" in source
    assert "raid_review_run_button" in source
    assert 'QPushButton("Load Fights")' in source
    assert 'QPushButton("Run Raid Review")' in source
    assert "def _load_raid_review_fights(self) -> None:" in source
    assert "self.raid_review_runner.list_lokkestiiz_fights(report_code)" in source
    assert "self.raid_review_runner.review_report(report_code, fight_ids)" in source
    assert "Raw research JSON is not required." in source
    assert "raid_review_fights_input" not in source


def test_raid_review_pull_picker_uses_checked_api_rows_as_review_input() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "def _selected_raid_review_fight_ids(self) -> tuple[int, ...]:" in source
    assert "Qt.CheckState.Checked" in source
    assert "Qt.ItemDataRole.UserRole" in source
    assert '"Use", "Fight", "Result", "Boss %", "Duration"' in source
    assert "Check at least one Lokkestiiz pull before running Raid Review." in source
