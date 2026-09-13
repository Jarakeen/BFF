from __future__ import annotations

"""Keep Build workspace inline surfaces synchronized with the active visual theme."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


def _surface_for_app(app: QApplication) -> str:
    return "#121315" if app.property("visualTheme") == VISUAL_THEME_RYLO else "#0C171B"


def apply_theme_aware_build_surface(widget) -> None:
    app = QApplication.instance()
    if app is None:
        return
    surface = _surface_for_app(app)
    widget.setProperty("themeAwareBuildSurface", True)
    widget.setAutoFillBackground(True)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(surface))
    palette.setColor(QPalette.ColorRole.Base, QColor(surface))
    widget.setPalette(palette)
    widget.setStyleSheet(f"background-color: {surface};")


def refresh_theme_aware_build_surfaces(app: QApplication) -> None:
    for widget in app.allWidgets():
        if bool(widget.property("themeAwareBuildSurface")):
            apply_theme_aware_build_surface(widget)


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import build_editor_inline_compat
    build_editor_inline_compat._force_dark_surface = apply_theme_aware_build_surface

    from ui.theme import theme_manager
    original_apply = theme_manager.ThemeManager.apply

    def apply_with_build_surface_refresh(self, target_app: QApplication) -> None:
        original_apply(self, target_app)
        refresh_theme_aware_build_surfaces(target_app)

    theme_manager.ThemeManager.apply = apply_with_build_surface_refresh
    _INSTALLED = True
