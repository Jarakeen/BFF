# ==================================================
# Black Feather Foundry
# ui/theme/theme_manager.py
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path
from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    COLOR_VISION_STANDARD,
    VISUAL_THEME_FOUNDRY,
    VISUAL_THEME_RYLO,
)
from ui.grimoire_theme import load_grimoire_stylesheet

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles


VISUAL_THEME_LABELS = {
    VISUAL_THEME_FOUNDRY: "Foundry Grimoire",
    VISUAL_THEME_RYLO: "Rylo Grayscale",
}

COLOR_VISION_LABELS = {
    COLOR_VISION_STANDARD: "Standard",
    COLOR_VISION_FRIENDLY: "Colorblind Friendly",
}


RYLO_GRAYSCALE_OVERRIDES = r"""
/* ============================================================
   RYLO GRAYSCALE
   Charcoal, steel, warm ash, restrained crimson accent.
   Decorative crimson is branding, never the only status cue.
   ============================================================ */
QWidget {
    background-color: #080B0E;
    color: #BEB6A6;
}
QMainWindow, QDialog, QScrollArea,
QScrollArea > QWidget > QWidget {
    background-color: #080B0E;
}

QWidget[foundryHeader="true"] {
    background-color: #0B0D10;
    border-bottom: 1px solid #343438;
}
QLabel[pageTitle="true"] {
    color: #D8D0C0;
}
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"] {
    color: #92918D;
}

QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #111316;
    background-image: none;
    border-left: 1px solid #4A4A4E;
    border-top: 1px solid #4A4A4E;
    border-right: 1px solid #26272A;
    border-bottom: 1px solid #222326;
}
QWidget[cardHeader="true"] {
    background-color: #17191C;
    border-bottom: 1px solid #3D3E42;
}
QLabel[cardTitle="true"] { color: #C8C0B1; }
QLabel[cardIcon="true"] { color: #A9A39A; }
QLabel[cardBadge="true"] {
    background-color: #1B1D20;
    color: #AAA7A0;
    border-color: #45464A;
}

QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #202226;
    background-image: none;
    color: #D0C8B9;
    border-left: 1px solid #55565A;
    border-top: 1px solid #55565A;
    border-right: 1px solid #2B2C30;
    border-bottom: 1px solid #27282C;
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel,
QWidget[foundryNoteCard="true"] QLabel,
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit,
QFrame[foundryNoteCard="true"] QPlainTextEdit,
QFrame[foundryNoteCard="true"] QTextEdit {
    color: #D0C8B9;
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #D2C8B6;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #111317;
    color: #D2CABC;
    border-left: 1px solid #303136;
    border-top: 1px solid #303136;
    border-right: 1px solid #56575B;
    border-bottom: 1px solid #56575B;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #17191D;
    border: 1px solid #8B0E14;
}

QPushButton {
    background-color: #15171A;
    color: #C9C1B3;
    border-left: 1px solid #4A4B50;
    border-top: 1px solid #4A4B50;
    border-right: 1px solid #25262A;
    border-bottom: 1px solid #25262A;
}
QPushButton:hover {
    background-color: #1D1F23;
    border-left-color: #6A6B70;
    border-top-color: #6A6B70;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #281416;
    color: #E0D6C5;
    border-left-color: #8B0E14;
    border-top-color: #8B0E14;
}

QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: #090B0E;
    border-color: #343438;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #B9B3A9;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #17191C;
    border-color: #393A3E;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #211214;
    color: #E0D6C5;
    border-color: #5F2024;
    border-left: 2px solid #8B0E14;
}

QTabWidget::pane { border-color: #3D3E42; background-color: #0E1013; }
QTabBar::tab {
    background-color: #111317;
    color: #989792;
    border-color: #333438;
}
QTabBar::tab:selected {
    background-color: #211214;
    color: #DDD3C3;
    border-color: #6E2328;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #0E1013;
    alternate-background-color: #15171A;
    color: #CBC4B7;
    gridline-color: #303136;
    selection-background-color: #2A2C31;
    selection-color: #F0E8D9;
}
QHeaderView::section {
    background-color: #181A1E;
    color: #BEB6A6;
    border-right: 1px solid #34353A;
    border-bottom: 1px solid #434449;
}

QScrollBar:vertical, QScrollBar:horizontal { background: #080B0E; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #404146; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #595A60; }

QLabel[heroTitle="true"] { color: #D4CABB; }
QLabel[heroSubtitle="true"] { color: #AAA39A; }
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: #101216;
    border-color: #44454A;
    color: #888781;
}
QLabel[timerValue="true"] { color: #D9CDBA; }
"""


COLORBLIND_FRIENDLY_OVERRIDES = r"""
/* ============================================================
   COLORBLIND FRIENDLY SEMANTIC OVERLAY
   Blue=safe, orange=danger, gold=warning. Color is supplemental;
   app surfaces should pair these roles with icon/shape/text cues.
   ============================================================ */
QLabel[successText="true"] { color: #3C9DFF; }
QLabel[criticalText="true"] { color: #E97917; }
QLabel[warningText="true"] { color: #F2C94C; }
QLabel[integrationState="true"] { color: #3C9DFF; }
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #241A13;
    color: #FFD7B0;
    border: 1px solid #E97917;
}
QProgressBar::chunk { background-color: #3C9DFF; }
"""


class Theme:
    """Compatibility wrapper for older callers that reference theme assets."""

    def __init__(self, name: str, folder: Path) -> None:
        self.name = name
        self.folder = folder
        self.logo = folder / "logo.ico"
        self.stylesheet = folder / "foundry.qss"
        self.preview = folder / "preview.png"
        self.background = folder / "background.png"
        self.colors = Colors
        self.fonts = Fonts
        self.metrics = Metrics
        self.roles = Roles


def _default_theme() -> Theme:
    return Theme(
        name="Black Feather Foundry",
        folder=get_resource_path("assets", "themes", "bff"),
    )


class ThemeManager:
    """Apply one visual skin plus one independent accessibility overlay."""

    def __init__(
        self,
        theme: Theme | None = None,
        preferences: AccessibilityPreferences | None = None,
    ) -> None:
        self._theme = theme or _default_theme()
        self.preferences = preferences or AccessibilityPreferences()

    @staticmethod
    def visual_theme_options() -> tuple[tuple[str, str], ...]:
        return tuple(VISUAL_THEME_LABELS.items())

    @staticmethod
    def color_vision_options() -> tuple[tuple[str, str], ...]:
        return tuple(COLOR_VISION_LABELS.items())

    def visual_theme(self) -> str:
        return self.preferences.visual_theme()

    def color_vision_mode(self) -> str:
        return self.preferences.color_vision_mode()

    def set_visual_theme(self, value: str) -> str:
        return self.preferences.set_visual_theme(value)

    def set_color_vision_mode(self, value: str) -> str:
        return self.preferences.set_color_vision_mode(value)

    def stylesheet_for_preferences(self) -> str:
        qss = load_grimoire_stylesheet()
        if self.visual_theme() == VISUAL_THEME_RYLO:
            qss += "\n" + RYLO_GRAYSCALE_OVERRIDES
        if self.color_vision_mode() == COLOR_VISION_FRIENDLY:
            qss += "\n" + COLORBLIND_FRIENDLY_OVERRIDES
        return qss

    def apply(self, app: QApplication) -> None:
        app.setStyle("Fusion")
        qss = self.stylesheet_for_preferences()
        if qss:
            app.setStyleSheet(qss)

        logo = get_resource_path("bff.ico")
        if logo.exists():
            app.setWindowIcon(QIcon(str(logo)))

        app.setProperty("visualTheme", self.visual_theme())
        app.setProperty("colorVisionMode", self.color_vision_mode())

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme

    @property
    def name(self):
        return VISUAL_THEME_LABELS.get(self.visual_theme(), self._theme.name)

    @property
    def logo(self):
        return self._theme.logo

    @property
    def stylesheet(self):
        return self._theme.stylesheet

    @property
    def preview(self):
        return self._theme.preview

    @property
    def background(self):
        return self._theme.background

    @property
    def colors(self):
        return self._theme.colors

    @property
    def fonts(self):
        return self._theme.fonts

    @property
    def metrics(self):
        return self._theme.metrics

    @property
    def roles(self):
        return self._theme.roles

    @property
    def sidebar_color(self):
        return self.colors.SIDEBAR

    @property
    def paper_color(self):
        return self.colors.PAPER

    @property
    def accent_color(self):
        return self.colors.ACCENT

    @property
    def title_font(self):
        return self.fonts.title()

    @property
    def body_font(self):
        return self.fonts.body()
