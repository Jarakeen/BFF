from __future__ import annotations

"""Collectibles assets for the additive Field Journal and City themes.

The original Foundry and Rylo collectible themes stay untouched. The two newer
visual themes get their own palette. When their dedicated badge sheets are not
installed yet, the dashboard deliberately falls back to the proven legacy badge
art and recolors it at render time instead of showing an empty badge slot.
"""

from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path
from services.accessibility_preferences import (
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO_CITY,
)

_INSTALLED = False

_FIELD_BADGE_TONES = (
    "#C8A46A",
    "#59AEB3",
    "#D9B977",
    "#7EB6B5",
    "#D1983D",
    "#91BFC0",
)
_CITY_BADGE_TONES = (
    "#7EA6B8",
    "#D0A35D",
    "#95A4AC",
    "#89B3C5",
    "#C8B58D",
    "#B9C5CC",
)


def _tone_for(label: str, labels: tuple[str, ...], tones: tuple[str, ...]) -> str:
    try:
        index = labels.index(label)
    except ValueError:
        index = 0
    return tones[index % len(tones)]


def _recolor_badge(pixmap: QPixmap | None, tone: str) -> QPixmap | None:
    """Recolor visible badge artwork while preserving dark engraved detail.

    The generated badge sprites contain deliberate dark shadows/outlines. A
    whole-image tint would turn their backgrounds into colored squares, so only
    medium/high-luminance pixels are remapped to the theme accent. Dark pixels
    remain dark and the original alpha is preserved.
    """
    if pixmap is None or pixmap.isNull():
        return None

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    target = QColor(tone)
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() <= 8:
                continue
            luminance = (54 * color.red() + 183 * color.green() + 19 * color.blue()) // 256
            if luminance < 44:
                continue
            strength = min(1.0, max(0.0, (luminance - 44) / 190.0))
            factor = 0.52 + 0.72 * strength
            image.setPixelColor(
                x,
                y,
                QColor(
                    min(255, round(target.red() * factor)),
                    min(255, round(target.green() * factor)),
                    min(255, round(target.blue() * factor)),
                    color.alpha(),
                ),
            )
    return QPixmap.fromImage(image)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_dashboard_page as dashboard

    field_theme = dashboard.DashboardTheme(
        key="field_journal",
        folder="bff/field_journal",
        accents=("#2F7A80", "#59AEB3", "#C8A46A", "#3F8E94", "#8CBFC1", "#D1983D"),
        panel="rgba(12, 32, 35, 232)",
        panel_hover="rgba(20, 53, 58, 238)",
        border="#765D35",
        border_hover="#C8A46A",
        title="#D9B977",
        subtitle="#59AEB3",
        text="#E5ECEB",
        muted="#91BFC0",
        meter_background="#081315",
        meter_border="#6E5733",
        meter_text="#F0E1BE",
        overall_chunk="#59AEB3",
        quote_background="#D6BD8C",
        quote_text="#2D281F",
    )
    city_theme = dashboard.DashboardTheme(
        key="rylo_city",
        folder="bff/city_night",
        accents=("#7EA6B8", "#D0A35D", "#95A4AC", "#5F8193", "#C8B58D", "#89B3C5"),
        panel="rgba(20, 25, 30, 238)",
        panel_hover="rgba(31, 40, 48, 242)",
        border="#665433",
        border_hover="#7EA6B8",
        title="#D0A35D",
        subtitle="#7EA6B8",
        text="#E7E9EA",
        muted="#AEB8BE",
        meter_background="#090C0F",
        meter_border="#555E64",
        meter_text="#E7E9EA",
        overall_chunk="#7EA6B8",
        quote_background="#252B30",
        quote_text="#E7E9EA",
    )

    labels = tuple(spec.label for spec in dashboard.DASHBOARD_SPECS)
    field_badges = {
        label: dashboard.SpriteRef("badges.jpg", 6, 4, index)
        for index, label in enumerate(labels)
    }
    city_badges = {
        label: dashboard.SpriteRef("badges.webp", 6, 4, index)
        for index, label in enumerate(labels)
    }

    original_active_theme = dashboard._active_theme
    original_theme_root = dashboard._theme_root
    original_badge_sprite = dashboard._badge_sprite
    original_number_sprite = dashboard._number_sprite

    def active_theme():
        app = QApplication.instance()
        visual_theme = str(app.property("visualTheme") if app is not None else "")
        if visual_theme == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL:
            return field_theme
        if visual_theme == VISUAL_THEME_RYLO_CITY:
            return city_theme
        return original_active_theme()

    def theme_root(theme):
        if theme.key == field_theme.key:
            return get_resource_path(
                "assets", "themes", "bff", "field_journal", "collectibles"
            )
        if theme.key == city_theme.key:
            return get_resource_path(
                "assets", "themes", "bff", "city_night", "collectibles"
            )
        return original_theme_root(theme)

    def dedicated_badge(theme, ref):
        root = Path(theme_root(theme))
        path = root / ref.filename
        if not path.is_file():
            return None
        return dashboard._sheet_for(theme, ref).cell(ref.index)

    def badge_sprite(theme, label: str):
        if theme.key == field_theme.key:
            ref = field_badges.get(label)
            dedicated = dedicated_badge(theme, ref) if ref else None
            if dedicated is not None and not dedicated.isNull():
                return dedicated
            legacy = original_badge_sprite(dashboard.BFF_THEME, label)
            return _recolor_badge(legacy, _tone_for(label, labels, _FIELD_BADGE_TONES))
        if theme.key == city_theme.key:
            ref = city_badges.get(label)
            dedicated = dedicated_badge(theme, ref) if ref else None
            if dedicated is not None and not dedicated.isNull():
                return dedicated
            legacy = original_badge_sprite(dashboard.RYLO_THEME, label)
            if legacy is None or legacy.isNull():
                legacy = original_badge_sprite(dashboard.BFF_THEME, label)
            return _recolor_badge(legacy, _tone_for(label, labels, _CITY_BADGE_TONES))
        return original_badge_sprite(theme, label)

    def number_sprite(theme, index: int):
        if theme.key == field_theme.key:
            source = original_number_sprite(dashboard.BFF_THEME, index)
            return _recolor_badge(source, "#C8A46A")
        if theme.key == city_theme.key:
            source = original_number_sprite(dashboard.RYLO_THEME, index)
            if source is None or source.isNull():
                source = original_number_sprite(dashboard.BFF_THEME, index)
            return _recolor_badge(source, "#D0A35D")
        return original_number_sprite(theme, index)

    dashboard.FIELD_JOURNAL_THEME = field_theme
    dashboard.RYLO_CITY_THEME = city_theme
    dashboard.FIELD_JOURNAL_BADGES = field_badges
    dashboard.RYLO_CITY_BADGES = city_badges
    dashboard._active_theme = active_theme
    dashboard._theme_root = theme_root
    dashboard._badge_sprite = badge_sprite
    dashboard._number_sprite = number_sprite

    _INSTALLED = True


__all__ = ["install"]
