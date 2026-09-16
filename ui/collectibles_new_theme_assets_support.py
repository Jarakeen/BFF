from __future__ import annotations

"""Collectibles assets for the additive Field Journal and City themes.

The original Foundry and Rylo collectible themes stay untouched. The two newer
visual themes get their own palette and badge sheets, cut from the corresponding
approved UI asset boards.
"""

from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path
from services.accessibility_preferences import (
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO,
    VISUAL_THEME_RYLO_CITY,
)

_INSTALLED = False


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

    field_badges = {
        spec.label: dashboard.SpriteRef("badges.jpg", 6, 4, index)
        for index, spec in enumerate(dashboard.DASHBOARD_SPECS)
    }
    city_badges = {
        spec.label: dashboard.SpriteRef("badges.jpg", 6, 4, index)
        for index, spec in enumerate(dashboard.DASHBOARD_SPECS)
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

    def badge_sprite(theme, label: str):
        if theme.key == field_theme.key:
            ref = field_badges.get(label)
            return dashboard._sheet_for(theme, ref).cell(ref.index) if ref else None
        if theme.key == city_theme.key:
            ref = city_badges.get(label)
            return dashboard._sheet_for(theme, ref).cell(ref.index) if ref else None
        return original_badge_sprite(theme, label)

    def number_sprite(theme, index: int):
        if theme.key in {field_theme.key, city_theme.key}:
            return None
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
