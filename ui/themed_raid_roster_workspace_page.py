from __future__ import annotations

"""Theme-aware wrapper for the unified raid Roster workspace.

The underlying workspace owns data flow and interaction. This wrapper only owns
visual-family presentation so the two legacy themes stay intact while the newer
Field Journal and City After Midnight themes can use their coordinating assets.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path
from services.accessibility_preferences import (
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO_CITY,
    is_rylo_visual_theme,
)
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage


class ThemedRaidRosterWorkspacePage(RaidRosterWorkspacePage):
    """Unified Roster workspace with explicit live theme-family refresh."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.refresh_theme_assets()

    @staticmethod
    def _visual_theme() -> str:
        app = QApplication.instance()
        return str(app.property("visualTheme") if app is not None else "")

    @classmethod
    def _rylo_family_active(cls) -> bool:
        return is_rylo_visual_theme(cls._visual_theme())

    def _legacy_sketch(self) -> Path:
        filename = (
            "roster_rylo_sketch.svg"
            if self._rylo_family_active()
            else "roster_foundry_sketch.svg"
        )
        return get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets", filename
        )

    def _asset_for(self, surface: str) -> Path:
        theme = self._visual_theme()
        if theme == VISUAL_THEME_RYLO_CITY:
            filename = f"roster_{surface}.jpg"
            candidate = get_resource_path(
                "assets", "themes", "bff", "city_night", "roster", filename
            )
            return Path(candidate) if Path(candidate).is_file() else self._legacy_sketch()
        if theme == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL:
            filename = f"roster_{surface}.jpg"
            candidate = get_resource_path(
                "assets", "themes", "bff", "field_journal", "roster", filename
            )
            return Path(candidate) if Path(candidate).is_file() else self._legacy_sketch()
        return self._legacy_sketch()

    def _apply_sketch(self, label, surface: str) -> None:
        if label is None:
            return
        path = self._asset_for(surface)
        pixmap = QPixmap(str(path)) if Path(path).exists() else QPixmap()
        label.clear()
        if pixmap.isNull():
            label.setText("Same people. Better prepared.")
            return
        label.setPixmap(
            pixmap.scaled(
                520,
                220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def refresh_theme_assets(self) -> None:
        """Refresh only theme-owned copy and artwork; never rebuild user state."""
        rylo = self._rylo_family_active()
        if hasattr(self, "header") and self.header is not None:
            self.header.subtitle.setText(
                "Built from static, stubbornness, and one more pull."
                if rylo
                else "People make the journey. Keep good records."
            )
            refresh_header = getattr(self.header, "refresh_visual_theme", None)
            if callable(refresh_header):
                refresh_header()

        self._apply_sketch(getattr(self, "player_sketch", None), "people")
        self._apply_sketch(getattr(self, "team_sketch", None), "team")


__all__ = ["ThemedRaidRosterWorkspacePage"]
