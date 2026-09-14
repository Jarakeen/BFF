from __future__ import annotations

"""Temporarily suppress screenshot/OCR build intake without deleting its implementation."""

_INSTALLED = False
_ORIGINAL_BUILD_UI = None


def disable_screenshot_import_control(page) -> bool:
    """Hide and disable the screenshot import control when present."""
    button = getattr(page, "import_screenshots_button", None)
    if button is None:
        return False
    button.setEnabled(False)
    button.setVisible(False)
    button.setToolTip(
        "Screenshot/OCR character and build import is temporarily disabled while the new raid-planning intake model is being stabilized."
    )
    return True


def _build_ui_without_screenshot_import(self) -> None:
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)
    disable_screenshot_import_control(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    _ORIGINAL_BUILD_UI = BuildsPage._build_ui
    BuildsPage._build_ui = _build_ui_without_screenshot_import
    _INSTALLED = True


__all__ = ["disable_screenshot_import_control", "install"]
