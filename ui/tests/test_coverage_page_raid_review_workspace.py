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


def test_raid_review_workspace_exposes_registry_driven_pull_picker() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "PerformanceRaidReviewRunnerService" in source
    assert "raid_review_encounter_combo" in source
    assert "self.raid_review_runner.available_encounters()" in source
    assert "raid_review_report_input" in source
    assert "raid_review_load_fights_button" in source
    assert "raid_review_fights_table" in source
    assert "raid_review_run_button" in source
    assert 'QPushButton("Load Fights")' in source
    assert 'QPushButton("Run Raid Review")' in source
    assert "def _load_raid_review_fights(self) -> None:" in source
    assert "self.raid_review_runner.list_fights(encounter_key, report_code)" in source
    assert "self.raid_review_runner.review_report(encounter_key, report_code, fight_ids)" in source
    assert "list_lokkestiiz_fights" not in source
    assert "raid_review_fights_input" not in source


def test_raid_review_pull_picker_uses_checked_api_rows_as_review_input() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "def _selected_raid_review_fight_ids(self) -> tuple[int, ...]:" in source
    assert "Qt.CheckState.Checked" in source
    assert "Qt.ItemDataRole.UserRole" in source
    assert '"Use", "Fight", "Result", "Boss %", "Duration"' in source
    assert "Check at least one {encounter_name} pull before running Raid Review." in source


def test_raid_review_picker_exposes_live_selection_evidence_mode() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "PerformanceRaidReviewSelectionModeService" in source
    assert "raid_review_selection_mode_label" in source
    assert "self.raid_review_fights_table.itemChanged.connect(self._raid_review_selection_changed)" in source
    assert "def _raid_review_selection_changed(self) -> None:" in source
    assert "def _update_raid_review_selection_mode(self) -> None:" in source
    assert "self.raid_review_selection_mode_service.classify(fight_ids)" in source
    assert 'f"{mode.display_name} • {mode.note}"' in source
    assert "blockSignals(True)" in source
    assert "blockSignals(False)" in source


def test_raid_review_encounter_selection_clears_stale_pull_rows() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "def _raid_review_encounter_changed(self) -> None:" in source
    assert "self.raid_review_fights_table.setRowCount(0)" in source
    assert "self.raid_review_run_button.setEnabled(False)" in source
    assert "self._update_raid_review_selection_mode()" in source


def test_raid_review_report_edit_clears_stale_pull_rows() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "self.raid_review_report_input.textChanged.connect(self._raid_review_report_changed)" in source
    assert "def _raid_review_report_changed(self) -> None:" in source
    method = source.split("def _raid_review_report_changed(self) -> None:", 1)[1].split("\n    def ", 1)[0]
    assert "self.raid_review_fights_table.setRowCount(0)" in method
    assert "self.raid_review_run_button.setEnabled(False)" in method
    assert "self._update_raid_review_selection_mode()" in method


def test_raid_review_api_work_runs_off_the_qt_gui_thread() -> None:
    page_source = Path("ui/coverage_page.py").read_text(encoding="utf-8")
    task_source = Path("ui/raid_review_async_task.py").read_text(encoding="utf-8")

    assert "from ui.raid_review_async_task import RaidReviewAsyncTask" in page_source
    assert "def _start_raid_review_task(" in page_source
    assert "task.start()" in page_source
    assert "task.succeeded.connect(on_success)" in page_source
    assert "task.failed.connect(" in page_source
    assert "class RaidReviewAsyncTask(QThread):" in task_source
    assert "result = self._operation()" in task_source
    assert "self.succeeded.emit(result)" in task_source
    assert "self.failed.emit(str(exc))" in task_source


def test_raid_review_disables_mutable_inputs_while_async_work_is_running() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert "def _set_raid_review_busy(self, busy: bool) -> None:" in source
    assert "self.raid_review_encounter_combo.setEnabled(not busy)" in source
    assert "self.raid_review_report_input.setEnabled(not busy)" in source
    assert "self.raid_review_fights_table.setEnabled(not busy)" in source
    assert "self.raid_review_load_fights_button.setEnabled(not busy)" in source
    assert '"A Raid Review API operation is already running."' in source
