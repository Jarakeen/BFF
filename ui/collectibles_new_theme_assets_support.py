from __future__ import annotations

"""Collectibles assets for the additive Field Journal and Urban Wilderness themes.

Field Journal retains its etched/recolored treatment. Urban Wilderness consumes the
approved dedicated badge sheets from assets/themes/bff/urban_wilderness/collectibles
without recoloring them again or falling back to legacy badge art.
"""

from pathlib import Path

from PySide6.QtCore import QRect, Qt
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


def _tone_for(label: str, labels: tuple[str, ...], tones: tuple[str, ...]) -> str:
    try:
        index = labels.index(label)
    except ValueError:
        index = 0
    return tones[index % len(tones)]


def _recolor_badge(pixmap: QPixmap | None, tone: str) -> QPixmap | None:
    """Recolor visible badge artwork while preserving dark engraved detail."""
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


def _trim_alpha(pixmap: QPixmap) -> QPixmap:
    """Trim transparent padding without clipping the badge's cardinal ornaments."""
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
    pad = 3
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(image.width() - 1, right + pad)
    bottom = min(image.height() - 1, bottom + pad)
    return pixmap.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def _prepare_city_badge(pixmap: QPixmap | None) -> QPixmap | None:
    """Remove authored black sheet space and return only the collectible medallion.

    The approved Urban Wilderness sheets were generated against pure black negative
    space rather than alpha. Only near-black connected background is removed here;
    dark navy/teal detail inside the medallions is deliberately preserved.
    """
    if pixmap is None or pixmap.isNull():
        return None

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    width = image.width()
    height = image.height()
    if width <= 0 or height <= 0:
        return pixmap

    # Flood-fill from the four corners so only exterior near-black space becomes
    # transparent. This avoids punching holes through legitimate dark badge detail.
    pending = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    visited: set[tuple[int, int]] = set()
    while pending:
        x, y = pending.pop()
        if (x, y) in visited or x < 0 or y < 0 or x >= width or y >= height:
            continue
        visited.add((x, y))
        color = image.pixelColor(x, y)
        if color.red() > 24 or color.green() > 24 or color.blue() > 24:
            continue
        color.setAlpha(0)
        image.setPixelColor(x, y, color)
        pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))

    return _trim_alpha(QPixmap.fromImage(image))


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
        folder="bff/urban_wilderness",
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

    # Approved Urban Wilderness sheets. No inset cropping: the generated badges
    # use nearly the full grid cell and their cardinal ornaments must remain intact.
    city_badges = {
        "Mounts": dashboard.SpriteRef("badges_1.png", 6, 4, 0),
        "Pets": dashboard.SpriteRef("badges_1.png", 6, 4, 1),
        "Armor Styles": dashboard.SpriteRef("badges_1.png", 6, 4, 2),
        "Costumes": dashboard.SpriteRef("badges_1.png", 6, 4, 5),
        "Personalities": dashboard.SpriteRef("badges_1.png", 6, 4, 6),
        "Emotes": dashboard.SpriteRef("badges_1.png", 6, 4, 7),
        "Mementos": dashboard.SpriteRef("badges_1.png", 6, 4, 9),
        "Furnishings": dashboard.SpriteRef("badges_1.png", 6, 4, 10),
        "Assistants": dashboard.SpriteRef("badges_1.png", 6, 4, 11),
        "Companions": dashboard.SpriteRef("badges_1.png", 6, 4, 12),
        "Body Markings": dashboard.SpriteRef("badges_1.png", 6, 4, 13),
        "Head Markings": dashboard.SpriteRef("badges_1.png", 6, 4, 14),
        "Hair": dashboard.SpriteRef("badges_1.png", 6, 4, 15),
        "Hats": dashboard.SpriteRef("badges_1.png", 6, 4, 16),
        "Facial Hair / Horns": dashboard.SpriteRef("badges_1.png", 6, 4, 18),
        "Piercing / Jewelry": dashboard.SpriteRef("badges_1.png", 6, 4, 19),
        "Tools & Upgrades": dashboard.SpriteRef("badges_1.png", 6, 4, 23),
        "Customized Actions": dashboard.SpriteRef("badges_1.png", 6, 4, 21),
        "Skins": dashboard.SpriteRef("badges_2.png", 3, 3, 0),
        "Weapon Styles": dashboard.SpriteRef("badges_2.png", 3, 3, 1),
        "Houses": dashboard.SpriteRef("badges_2.png", 3, 3, 2),
        "Polymorphs": dashboard.SpriteRef("badges_2.png", 3, 3, 3),
        "Facial Accessories": dashboard.SpriteRef("badges_2.png", 3, 3, 4),
        "Fragments": dashboard.SpriteRef("badges_2.png", 3, 3, 5),
        "Motifs": dashboard.SpriteRef("badges_2.png", 3, 3, 6),
        "Antiquities": dashboard.SpriteRef("badges_2.png", 3, 3, 7),
        "Lorebooks": dashboard.SpriteRef("badges_2.png", 3, 3, 8),
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
                "assets", "themes", "bff", "urban_wilderness", "collectibles"
            )
        return original_theme_root(theme)

    def dedicated_badge(theme, ref):
        if ref is None:
            return None
        root = Path(theme_root(theme))
        path = root / ref.filename
        if not path.is_file():
            return None
        source = dashboard._sheet_for(theme, ref).cell(ref.index)
        return _prepare_city_badge(source) if theme.key == city_theme.key else source

    def field_etched_badge(label: str):
        """Use the canonical BFF PNG badge assets; never decode the damaged JPEG sheet."""
        return original_badge_sprite(dashboard.BFF_THEME, label)

    def badge_sprite(theme, label: str):
        if theme.key == field_theme.key:
            source = field_etched_badge(label)
            return _recolor_badge(source, _tone_for(label, labels, _FIELD_BADGE_TONES))

        if theme.key == city_theme.key:
            # Use the approved art exactly as authored after removing only the
            # generated black sheet background. Never fall back to old badge art.
            return dedicated_badge(city_theme, city_badges.get(label))

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
