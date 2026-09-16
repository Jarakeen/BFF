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
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO,
    VISUAL_THEME_RYLO_CITY,
)
from ui.grimoire_theme import load_grimoire_stylesheet

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles


VISUAL_THEME_LABELS = {
    VISUAL_THEME_FOUNDRY: "Foundry Grimoire",
    VISUAL_THEME_RYLO: "Rylo Grayscale",
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL: "Foundry · Field Journal",
    VISUAL_THEME_RYLO_CITY: "Rylo · City After Midnight",
}

COLOR_VISION_LABELS = {
    COLOR_VISION_STANDARD: "Standard",
    COLOR_VISION_FRIENDLY: "Colorblind Friendly",
}


FOUNDRY_OVERVIEW_ACCENTS = r"""
/* Overview: quiet teal for identity and progress, amber for the main action. */
QWidget[operationsOverview="true"] QLabel[overviewPlayerName="true"],
QWidget[operationsOverview="true"] QLabel[overviewGoalName="true"] {
    color: #85C8CA;
}
QWidget[operationsOverview="true"] QProgressBar::chunk {
    background-color: #58AEB3;
}
QWidget[operationsOverview="true"] QProgressBar[overviewAttribute="health"]::chunk {
    background-color: #C96569;
}
QWidget[operationsOverview="true"] QProgressBar[overviewAttribute="stamina"]::chunk {
    background-color: #78B887;
}
QWidget[operationsOverview="true"] QProgressBar[overviewAttribute="magicka"]::chunk {
    background-color: #73A9D8;
}
QWidget[operationsOverview="true"] QFrame[overviewAccent="teal"] {
    border-left: 3px solid #58AEB3;
}

QPushButton[newBuildAction="true"] {
    background-color: #D1983D;
    color: #0C171B;
    border: 1px solid #C8A46A;
    border-radius: 17px;
    padding: 8px 22px;
    font-weight: 700;
}
QPushButton[newBuildAction="true"]:hover { background-color: #DCAA57; }
QPushButton[newBuildAction="true"]:pressed { background-color: #B97F2F; }
QPushButton[newBuildAction="true"]:disabled {
    background-color: #6D5A37;
    color: #BFC8C6;
}
QFrame#newBuildPullDown {
    border: 1px solid #C8A46A;
    border-radius: 18px;
    background-color: rgba(47, 122, 128, 28);
}
QLabel#newBuildEyebrow { font-weight: 700; letter-spacing: 1px; }
QLabel#newBuildTitle { font-size: 24px; font-weight: 700; }
"""


RYLO_GRAYSCALE_OVERRIDES = r"""
/* ============================================================
   LEGACY RYLO GRAYSCALE
   Kept intact as the original dark charcoal + restrained crimson skin.
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
QLabel[pageTitle="true"] { color: #D8D0C0; }
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"] { color: #92918D; }
QFrame[foundryCard="true"], QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
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
QPushButton:hover { background-color: #1D1F23; }
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
QPushButton[nav="true"], QPushButton[settingsNav="true"] { color: #B9B3A9; }
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #211214;
    color: #E0D6C5;
    border-color: #5F2024;
    border-left: 2px solid #8B0E14;
}
QTabWidget::pane { border-color: #3D3E42; background-color: #0E1013; }
QTabBar::tab { background-color: #111317; color: #989792; border-color: #333438; }
QTabBar::tab:selected { background-color: #211214; color: #DDD3C3; border-color: #6E2328; }
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
QLabel[heroTitle="true"] { color: #D4CABB; }
QLabel[heroSubtitle="true"] { color: #AAA39A; }
"""


FOUNDRY_FIELD_JOURNAL_OVERRIDES = r"""
/* ============================================================
   FOUNDRY FIELD JOURNAL
   Collectibles-inspired teal/antique-gold cards, restrained fantasy linework,
   parchment notes, and the same dense information hierarchy across raid pages.
   ============================================================ */
QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #09181B;
    color: #E5ECEB;
}
QWidget[foundryHeader="true"] {
    background-color: #0B1D21;
    border-bottom: 1px solid #806333;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] { color: #E6E1D4; }
QLabel[pageSubtitle="true"], QLabel[heroSubtitle="true"] { color: #BFC8C6; }
QLabel[departmentLabel="true"] { color: #59AEB3; }
QFrame[foundryCard="true"], QFrame[bookPanel="true"], QWidget[bookPanel="true"],
QFrame[rosterMetricCard="true"] {
    background-color: #0C2023;
    border: 1px solid #765D35;
    border-radius: 4px;
}
QWidget[cardHeader="true"] {
    background-color: #10282C;
    border-bottom: 1px solid #6E5733;
}
QLabel[cardTitle="true"], QLabel[rosterMetricTitle="true"] {
    color: #D9B977;
    font-weight: 700;
}
QLabel[rosterMetricOrdinal="true"] {
    color: #D1983D;
    border: 1px solid #806333;
    border-radius: 12px;
    min-width: 22px;
    min-height: 22px;
}
QLabel[rosterMetricIcon="true"] { color: #D9B977; font-size: 24px; }
QLabel[rosterMetricValue="true"] { color: #E5ECEB; font-size: 20px; font-weight: 700; }
QProgressBar[rosterMetricProgress="true"] {
    min-height: 8px;
    max-height: 8px;
    background-color: #081315;
    border: 1px solid #6E5733;
    border-radius: 4px;
}
QProgressBar[rosterMetricProgress="true"]::chunk { background-color: #59AEB3; border-radius: 3px; }
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #D6BD8C;
    color: #2D281F;
    border: 1px solid #9D7E48;
    border-radius: 2px;
}
QFrame[parchment="true"] QLabel, QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel, QWidget[foundryNoteCard="true"] QLabel { color: #2D281F; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #0A191C;
    color: #E5ECEB;
    border: 1px solid #4F696C;
    border-radius: 3px;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus { border: 2px solid #C8A46A; }
QPushButton { background-color: #10282C; color: #E5ECEB; border: 1px solid #54757A; border-radius: 3px; }
QPushButton:hover { background-color: #15353A; border-color: #C8A46A; }
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #1F5960;
    color: #F1F4F3;
    border: 1px solid #C8A46A;
    border-left: 3px solid #59AEB3;
}
QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: #08171A;
    border-right: 1px solid #6E5733;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] { color: #D3DAD8; background-color: transparent; }
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #18363A;
    color: #F0E1BE;
    border: 1px solid #806333;
    border-left: 4px solid #D1983D;
}
QTabBar::tab { background-color: #0D2327; color: #BFC8C6; border: 1px solid #4D5755; }
QTabBar::tab:selected { background-color: #15373C; color: #F0E1BE; border-bottom: 3px solid #59AEB3; }
QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #0A191C;
    alternate-background-color: #0E2327;
    color: #E5ECEB;
    gridline-color: #2D484B;
    selection-background-color: #1F4D53;
    selection-color: #FFFFFF;
    border: 1px solid #765D35;
}
QHeaderView::section {
    background-color: #10282C;
    color: #D9B977;
    border-right: 1px solid #364F52;
    border-bottom: 1px solid #765D35;
}
"""


RYLO_CITY_OVERRIDES = r"""
/* ============================================================
   RYLO CITY AFTER MIDNIGHT
   New theme. The legacy Rylo Grayscale skin is intentionally untouched.
   Colorblind-safe and seizure-aware by construction: no flashing, pulsing,
   animated gradients, or color-only state semantics.
   ============================================================ */
QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #0B0D10;
    color: #E7E9EA;
}
QWidget { color: #E7E9EA; }
QWidget[foundryHeader="true"] {
    background-color: #11161B;
    border-bottom: 1px solid #675332;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] { color: #E7E9EA; }
QLabel[pageSubtitle="true"], QLabel[heroSubtitle="true"] { color: #AEB8BE; }
QLabel[departmentLabel="true"] { color: #7EA6B8; }
QFrame[foundryCard="true"], QFrame[bookPanel="true"], QWidget[bookPanel="true"],
QFrame[rosterMetricCard="true"] {
    background-color: #14191E;
    border: 1px solid #665433;
    border-radius: 3px;
}
QWidget[cardHeader="true"] { background-color: #191F25; border-bottom: 1px solid #4B5055; }
QLabel[cardTitle="true"], QLabel[rosterMetricTitle="true"] { color: #D0A35D; font-weight: 700; }
QLabel[rosterMetricOrdinal="true"] {
    color: #D0A35D;
    border: 1px solid #665433;
    border-radius: 12px;
    min-width: 22px;
    min-height: 22px;
}
QLabel[rosterMetricIcon="true"] { color: #C8B58D; font-size: 24px; }
QLabel[rosterMetricValue="true"] { color: #E7E9EA; font-size: 20px; font-weight: 700; }
QProgressBar[rosterMetricProgress="true"], QProgressBar {
    background-color: #090C0F;
    color: #E7E9EA;
    border: 1px solid #555E64;
    border-radius: 3px;
}
QProgressBar[rosterMetricProgress="true"]::chunk, QProgressBar::chunk { background-color: #7EA6B8; }
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #D0B98C;
    color: #25231F;
    border: 1px solid #88734B;
    border-radius: 2px;
}
QFrame[parchment="true"] QLabel, QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel, QWidget[foundryNoteCard="true"] QLabel { color: #25231F; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #11161B;
    color: #E7E9EA;
    selection-background-color: #385467;
    selection-color: #FFFFFF;
    border: 1px solid #57636B;
    border-radius: 3px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus { border: 2px solid #D0A35D; }
QPushButton { background-color: #171D22; color: #E7E9EA; border: 1px solid #56616A; border-radius: 3px; }
QPushButton:hover { background-color: #202932; border-color: #7EA6B8; }
QPushButton:pressed { background-color: #101419; border: 2px solid #D0A35D; }
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #253542;
    color: #FFFFFF;
    border: 1px solid #7599AA;
    border-left: 4px solid #7EA6B8;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3A2B1D;
    color: #FFE4C2;
    border: 2px solid #E79643;
}
QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: #0C1014;
    border-right: 1px solid #4C5359;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] { color: #C5CDD2; background-color: transparent; }
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover { background-color: #171D22; }
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #23313B;
    color: #FFFFFF;
    border: 1px solid #566E7C;
    border-left: 4px solid #7EA6B8;
}
QTabBar::tab { background-color: #13191E; color: #B5BDC2; border: 1px solid #3F474E; }
QTabBar::tab:selected { background-color: #24323C; color: #FFFFFF; border-bottom: 3px solid #7EA6B8; }
QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #101419;
    alternate-background-color: #171C21;
    color: #E0E5E7;
    gridline-color: #343D43;
    selection-background-color: #324B5B;
    selection-color: #FFFFFF;
    border: 1px solid #535B61;
}
QHeaderView::section {
    background-color: #192027;
    color: #D5C8AA;
    border-right: 1px solid #3F474E;
    border-bottom: 1px solid #665433;
}
QLabel[successText="true"], QLabel[integrationState="true"] { color: #79BEE8; }
QLabel[criticalText="true"] { color: #F0A05A; }
QLabel[warningText="true"] { color: #E0BE57; }
QLabel[specialText="true"] { color: #B99AE8; }
QLabel[neutralText="true"] { color: #AAB2B7; }
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
        theme = self.visual_theme()
        if theme == VISUAL_THEME_RYLO:
            qss += "\n" + RYLO_GRAYSCALE_OVERRIDES
        elif theme == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL:
            qss += "\n" + FOUNDRY_OVERVIEW_ACCENTS
            qss += "\n" + FOUNDRY_FIELD_JOURNAL_OVERRIDES
        elif theme == VISUAL_THEME_RYLO_CITY:
            qss += "\n" + RYLO_CITY_OVERRIDES
        else:
            qss += "\n" + FOUNDRY_OVERVIEW_ACCENTS
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
