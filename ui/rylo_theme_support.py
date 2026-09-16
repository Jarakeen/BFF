from __future__ import annotations

"""Visual-theme Settings integration.

Legacy ``foundry_grimoire`` and ``rylo_grayscale`` remain unchanged. The newer
Collectibles-inspired Foundry and city-night Rylo directions are separate theme
keys registered by ``ThemeManager`` rather than replacements for the old skins.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from services.accessibility_preferences import (
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO_CITY,
)

_INSTALLED = False


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager
    from ui import settings_page

    original_load_settings = settings_page.SettingsPage.load_settings

    def appearance_page_with_themes(self):
        page, layout = self._page_shell("Appearance")

        title = QLabel("Visual Theme")
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)

        self.visual_theme_combo = QComboBox()
        for key, label in theme_manager.ThemeManager.visual_theme_options():
            self.visual_theme_combo.addItem(label, key)
        layout.addWidget(self.visual_theme_combo)

        description = QLabel(
            "Four independent skins are available. Foundry Grimoire and Rylo Grayscale "
            "remain the original themes. Foundry · Field Journal uses the dense teal/gold "
            "Collectibles language with parchment sketches. Rylo · City After Midnight uses "
            "charcoal, steel blue, muted amber, city sketches, and the same page geometry."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        accessibility = QLabel(
            "Rylo · City After Midnight is colorblind-safe and seizure-aware by design: "
            "status meaning is paired with text/shape, not hue alone, and the skin defines "
            "no flashing, pulsing, strobing, or animated-gradient effects."
        )
        accessibility.setWordWrap(True)
        accessibility.setProperty("muted", True)
        layout.addWidget(accessibility)

        note = QLabel("FIELD JOURNAL  ·  CITY AFTER MIDNIGHT  ·  SAME APP, DIFFERENT WEATHER")
        note.setWordWrap(True)
        note.setProperty("integrationState", True)
        layout.addWidget(note)

        def apply_selected_theme(index: int) -> None:
            key = self.visual_theme_combo.itemData(index)
            if not key:
                return
            manager = theme_manager.ThemeManager()
            manager.set_visual_theme(str(key))
            manager.apply(app)

            from ui.ux_icons import refresh_theme_icons
            refresh_theme_icons(app)

            for widget in app.topLevelWidgets():
                sidebar = getattr(widget, "sidebar", None)
                if sidebar is not None and hasattr(sidebar, "refresh_brand_mark"):
                    sidebar.refresh_brand_mark()

                pages = getattr(widget, "pages", {})
                if not isinstance(pages, dict):
                    continue
                for route in ("roster_workspace", "roster_page"):
                    page_widget = pages.get(route)
                    refresh_assets = getattr(page_widget, "refresh_theme_assets", None)
                    if callable(refresh_assets):
                        refresh_assets()

            label = self.visual_theme_combo.currentText()
            if str(key) == VISUAL_THEME_RYLO_CITY:
                self.status.success(label + " · colorblind-safe city skin enabled.")
            elif str(key) == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL:
                self.status.success(label + " · field-journal skin enabled.")
            else:
                self.status.success("Visual theme: " + label + ".")

        self.visual_theme_combo.currentIndexChanged.connect(apply_selected_theme)
        return page

    def load_settings_with_theme(self):
        original_load_settings(self)
        combo = getattr(self, "visual_theme_combo", None)
        if combo is None:
            return
        active = theme_manager.ThemeManager().visual_theme()
        index = combo.findData(active)
        combo.blockSignals(True)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    settings_page.SettingsPage._appearance_page = appearance_page_with_themes
    settings_page.SettingsPage.load_settings = load_settings_with_theme

    _INSTALLED = True
