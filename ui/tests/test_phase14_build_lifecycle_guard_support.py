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


def test_phase14_build_lifecycle_guard_checks_shiboken_validity() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "from shiboken6 import isValid" in source
    assert "def _command_center_alive(page) -> bool:" in source
    assert '"phase14_library_tabs"' in source
    assert '"phase14_build_table"' in source
    assert "if not _command_center_alive(page):" in source


def test_phase14_build_lifecycle_guard_rebuilds_presentation_only() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "replacement = command_center._create_command_center(self)" in source
    assert "self.splitter.replaceWidget(0, replacement)" in source
    assert "command_center._wire_new_build_button(self)" in source
    assert "command_center._quiet_overview_action_bar(self)" in source
    assert "eso.db" not in source
