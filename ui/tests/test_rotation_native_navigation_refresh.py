from pathlib import Path


def test_rotation_navigation_natively_reloads_long_lived_saved_build_state() -> None:
    source = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )

    show_event = source.split("def showEvent(self, event)", 1)[1].split(
        "def _refresh_saved_builds", 1
    )[0]
    refresh = source.split("def _refresh_saved_builds", 1)[1].split(
        "def _install_canonical_recovery_policy_controls", 1
    )[0]

    assert "self._refresh_saved_builds()" in show_event
    assert "except Exception as exc" in show_event
    assert "super().showEvent(event)" in show_event
    assert "self.roster = self.build_service.load()" in refresh
    assert "self._character_changed()" in refresh
    assert "self._refresh_build_context()" in refresh


def test_rotation_navigation_preserves_character_and_build_selection() -> None:
    source = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )
    refresh = source.split("def _refresh_saved_builds", 1)[1].split(
        "def _install_canonical_recovery_policy_controls", 1
    )[0]

    assert "selected_character = str(self.character_combo.currentData()" in refresh
    assert "selected_build = str(self.build_combo.currentText()" in refresh
    assert "self.character_combo.findData(selected_character)" in refresh
    assert "self.build_combo.findText(selected_build)" in refresh


def test_obsolete_rotation_navigation_refresh_installer_is_not_composed() -> None:
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "rotation_navigation_refresh_support" not in bootstrap
