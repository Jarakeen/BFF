from __future__ import annotations

from pathlib import Path


def test_rotation_navigation_refresh_reloads_long_lived_saved_build_state() -> None:
    source = Path("ui/rotation_navigation_refresh_support.py").read_text(encoding="utf-8")

    assert "page.roster = page.build_service.load()" in source
    assert "page._character_changed()" in source
    assert "CanonicalRotationDashboardPage.showEvent = show_event_with_saved_build_refresh" in source
    assert "except Exception as exc" in source


def test_rotation_navigation_refresh_support_is_installed() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_rotation_navigation_refresh_support" in source
    assert "install_rotation_navigation_refresh_support()" in source
