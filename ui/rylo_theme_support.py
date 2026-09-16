from __future__ import annotations

"""City After Midnight theme integration.

Historical theme keys remain readable for compatibility, but the application now
presents a single visual skin: Rylo · City After Midnight.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from services.accessibility_preferences import VISUAL_THEME_RYLO_CITY

_INSTALLED = False


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.collectibles_new_theme_assets_support import install as install_collectibles_theme_assets
    from ui.theme import theme_manager
    from ui import settings_page

    install_collectibles_theme_assets()

    # Normalize every install to the one supported skin before pages are built.
    manager = theme_manager.ThemeManager()
    manager.set_visual_theme(VISUAL_THEME_RYLO_CITY)
    manager.apply(app)

    original_load_settings = settings_page.SettingsPage.load_settings

    def appearance_page_with_themes(self):
        page, layout = self._page_shell("Appearance")

        title = QLabel("Visual Theme")
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)

        self.visual_theme_combo = QComboBox()
        self.visual_theme_combo.addItem("Rylo · City After Midnight", VISUAL_THEME_RYLO_CITY)
        self.visual_theme_combo.setEnabled(False)
        layout.addWidget(self.visual_theme_combo)

        description = QLabel(
            "City After Midnight is the active FoundryDock skin: charcoal, steel blue, "
            "muted amber, city sketches, parchment scraps, and Collectibles-style cards."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        accessibility = QLabel(
            "The skin is colorblind-friendly and seizure-aware: state meaning uses text, "
            "icons, and shape in addition to color, with no flashing, pulsing, strobing, "
            "or animated-gradient effects."
        )
        accessibility.setWordWrap(True)
        accessibility.setProperty("muted", True)
        layout.addWidget(accessibility)

        note = QLabel("CITY AFTER MIDNIGHT  ·  ONE VISUAL LANGUAGE  ·  LESS THEME DRAMA")
        note.setWordWrap(True)
        note.setProperty("integrationState", True)
        layout.addWidget(note)
        return page

    def load_settings_with_theme(self):
        original_load_settings(self)
        combo = getattr(self, "visual_theme_combo", None)
        if combo is not None:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    settings_page.SettingsPage._appearance_page = appearance_page_with_themes
    settings_page.SettingsPage.load_settings = load_settings_with_theme

    _INSTALLED = True
