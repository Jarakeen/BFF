from __future__ import annotations

"""Final presentation pass for Urban Wilderness collectible badge artwork.

The badge-sheet cleanup now happens in ``collectibles_new_theme_assets_support`` by
keeping the centered medallion component. This layer only normalizes the displayed
size so every dashboard card uses the same visual footprint.
"""

from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO_CITY

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_dashboard_page as dashboard

    original_set_sprite = dashboard.ProgressTile._set_sprite

    def set_sprite(label, pixmap, size: int) -> bool:
        app = QApplication.instance()
        visual_theme = str(app.property("visualTheme") if app is not None else "")
        if visual_theme == VISUAL_THEME_RYLO_CITY and size >= 70:
            label.setFixedSize(90, 90)
            label.setStyleSheet("background: transparent; border: none; padding: 0;")
            return original_set_sprite(label, pixmap, 86)
        return original_set_sprite(label, pixmap, size)

    dashboard.ProgressTile._set_sprite = staticmethod(set_sprite)
    _INSTALLED = True


__all__ = ["install"]
