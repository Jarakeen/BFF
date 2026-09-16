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
from services.accessibility_preferences import is_rylo_visual_theme
from ui.raid_roster_workspace_page import RaidRosterWorkspacePage


class ThemedRaidRosterWorkspacePage(RaidRosterWorkspacePage):
    """Unified Roster workspace with explicit live theme-family refresh."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.refresh_theme_assets()

    @staticmethod
    def _rylo_family_active() -> bool:
        app = QApplication.instance()
        theme = app.property("visualTheme") if app is not None else ""
        return is_rylo_visual_theme(str(theme or ""))

    def _apply_sketch(self, label) -> None:
        if label is None:
            return
        filename = (
            "roster_rylo_sketch.svg"
            if self._rylo_family_active()
            else "roster_foundry_sketch.svg"
        )
        path = get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets", filename
        )
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

        self._apply_sketch(getattr(self, "player_sketch", None))
        self._apply_sketch(getattr(self, "team_sketch", None))


__all__ = ["ThemedRaidRosterWorkspacePage"]
