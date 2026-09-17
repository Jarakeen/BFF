from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_lifecycle_guard_support


def _source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def test_phase14_build_lifecycle_guard_installs_after_inspector() -> None:
    source = _source(application_workspace_bootstrap)

    assert "install_phase14_build_lifecycle_guard_support()" in source
    assert source.index("install_phase14_build_inspector_support()") < source.index(
        "install_phase14_build_lifecycle_guard_support()"
    )


def test_phase14_build_lifecycle_guard_checks_shiboken_validity_and_attachment() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "from shiboken6 import isValid" in source
    assert "def _command_center_alive(page) -> bool:" in source
    assert "def _command_center_attached(page) -> bool:" in source
    assert '"phase14_library_tabs"' in source
    assert '"phase14_build_table"' in source
    assert "return splitter.widget(0) is current" in source
    assert "if not _command_center_attached(page):" in source


def test_phase14_build_lifecycle_guard_repairs_actual_themed_build_page_boundary() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "from ui.themed_builds_page import BuildsPage as ThemedBuildsPage" in source
    assert "original_themed_build_ui = ThemedBuildsPage._build_ui" in source
    assert "def build_themed_ui_with_final_repair(self):" in source
    assert "ThemedBuildsPage._build_ui = build_themed_ui_with_final_repair" in source


def test_phase14_build_lifecycle_guard_rebuilds_and_shows_presentation_only() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "replacement = command_center._create_command_center(page)" in source
    assert "splitter.replaceWidget(0, replacement)" in source
    assert "command_center._wire_new_build_button(page)" in source
    assert "command_center._quiet_overview_action_bar(page)" in source
    assert "tabs.setCurrentIndex(0)" in source
    assert "splitter.show()" in source
    assert "eso.db" not in source
