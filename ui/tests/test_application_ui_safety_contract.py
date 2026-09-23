from __future__ import annotations

from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_main_window_guards_navigation_and_close_for_dirty_pages() -> None:
    source = _source("ui/main_window.py")
    assert "confirm_unsaved_changes" in source
    assert "_confirm_unsaved_navigation" in source
    assert "def closeEvent" in source
    assert "_dirty_pages()" in source
    assert "_install_page_safety_badges()" in source


def test_shared_safety_contract_fails_closed_on_save_or_discard_failure() -> None:
    source = _source("ui/ui_safety.py")
    assert "QMessageBox.StandardButton.Save" in source
    assert "QMessageBox.StandardButton.Discard" in source
    assert "QMessageBox.StandardButton.Cancel" in source
    assert "This page does not expose a safe save action." in source
    assert "This page cannot safely discard its current edits." in source
    assert "The page is still reporting unsaved changes after Save." in source
    assert "Save Failed" in source


def test_raid_plan_has_drafts_archive_delete_confirmation_and_snapshot() -> None:
    source = _source("ui/raid_plan_persistence_page.py")
    assert "UiDraftRecoveryService" in source
    assert "_autosave_recovery_draft" in source
    assert "Recovered Raid Plan Draft" in source
    assert "toggle_archive_selected_plan" in source
    assert 'QPushButton("Archive")' in source
    assert "confirm_destructive_action" in source
    assert '_safety_snapshots.create(f"delete-raid-plan-' in source


def test_comp_maker_has_recovery_drafts_replacement_confirmation_and_snapshot() -> None:
    shell = _source("ui/comp_builder_phase14_shell_support.py")
    intake = _source("ui/comp_builder_roster_intake_support.py")
    assert "UiDraftRecoveryService" in shell
    assert "_save_comp_recovery_draft" in shell
    assert "confirm_replacement" in shell
    assert "_comp_snapshot_service(page).create" in shell
    assert "confirm_replacement" in intake
    assert "UserSafetySnapshotService().create" in intake


def test_encounter_map_has_draft_recovery_context_guards_and_safe_delete() -> None:
    source = _source("ui/application_ui_safety_support.py")
    assert "_save_map_draft" in source
    assert "_offer_map_recovery" in source
    assert 'action_text="switch bosses"' in source
    assert 'action_text="switch Raid Plans"' in source
    assert "Remove Raid Map from Finch" in source
    assert "Delete Raid Map Item" in source


def test_team_schedule_and_live_raid_join_global_dirty_state_contract() -> None:
    roster = _source("ui/themed_roster_page.py")
    live = _source("ui/city_live_raid_page.py")
    assert "_schedule_has_pending_changes" in roster
    assert 'action_text="switch Teams"' in roster
    assert "UserSafetySnapshotService().create" in roster
    assert "confirm_destructive_action" in roster
    assert "def has_pending_changes(self)" in live
    assert 'action_text="switch Live Raid plans"' in live
    assert "Clear Raid Map Link" in live
    assert "confirm_replacement" in live


def test_build_reuse_requires_confirmation_before_replacing_existing_build() -> None:
    source = _source("ui/build_reuse_template_support.py")
    assert "_existing_build_for" in source
    assert "Replace Existing Build" in source
    assert "Update Build Template" in source
    assert "UserSafetySnapshotService().create" in source


def test_high_risk_roster_operations_snapshot_before_mutation() -> None:
    for path in (
        "ui/roster_import_workflow.py",
        "ui/roster_team_merge_support.py",
        "ui/raid_roster_workspace_page.py",
        "ui/roster_page.py",
        "ui/phase5_build_delete_support.py",
    ):
        source = _source(path)
        assert "UserSafetySnapshotService" in source, path


def test_active_theme_styles_all_save_state_badges_with_text_and_shape() -> None:
    source = _source("ui/theme/theme_manager.py")
    for state in ("saved", "dirty", "saving", "failed"):
        assert f'QLabel[uiSafetyState="{state}"]' in source
