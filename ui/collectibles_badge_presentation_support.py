from __future__ import annotations

"""Final presentation pass for Urban Wilderness collectible badge artwork.

The approved generated sheets contain a little neighboring artwork at some cell edges.
This pass trims only that outer spill, preserves the badge itself, and presents the art
large and frameless directly on the dark card surface.
"""

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO_CITY

_INSTALLED = False


def _trim_alpha(pixmap: QPixmap) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() <= 8:
                continue
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
    if right < left or bottom < top:
        return pixmap
    return pixmap.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_dashboard_page as dashboard
    from ui import collectibles_new_theme_assets_support as assets_support

    original_prepare = assets_support._prepare_city_badge
    original_set_sprite = dashboard.ProgressTile._set_sprite

    def prepare_city_badge(pixmap):
        prepared = original_prepare(pixmap)
        if prepared is None or prepared.isNull():
            return prepared

        # Generated grid sheets can leave slivers of the neighboring medallion
        # at the extreme left/right edges. Remove only a narrow outer gutter,
        # then trim alpha so the badge sits directly on the card background.
        gutter_x = max(1, round(prepared.width() * 0.045))
        gutter_y = max(0, round(prepared.height() * 0.01))
        width = max(1, prepared.width() - (gutter_x * 2))
        height = max(1, prepared.height() - (gutter_y * 2))
        cropped = prepared.copy(QRect(gutter_x, gutter_y, width, height))
        return _trim_alpha(cropped)

    def set_sprite(label, pixmap, size: int) -> bool:
        app = QApplication.instance()
        visual_theme = str(app.property("visualTheme") if app is not None else "")
        if visual_theme == VISUAL_THEME_RYLO_CITY and size >= 70:
            label.setFixedSize(120, 120)
            label.setStyleSheet("background: transparent; border: none; padding: 0;")
            return original_set_sprite(label, pixmap, 116)
        return original_set_sprite(label, pixmap, size)

    assets_support._prepare_city_badge = prepare_city_badge
    dashboard.ProgressTile._set_sprite = staticmethod(set_sprite)
    _INSTALLED = True


__all__ = ["install"]
