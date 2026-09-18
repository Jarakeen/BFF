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
    VISUAL_THEME_URBAN_WILDERNESS,
)
from ui.grimoire_theme import load_grimoire_stylesheet

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles


VISUAL_THEME_LABELS = {
    VISUAL_THEME_URBAN_WILDERNESS: "Urban Wilderness",
}

COLOR_VISION_LABELS = {
    COLOR_VISION_FRIENDLY: "Colorblind Friendly",
}


URBAN_WILDERNESS_OVERRIDES = r"""
/* ============================================================
   URBAN WILDERNESS
   One low-stimulation theme combining City After Midnight with
   Field Journal. Steel blue + muted amber + parchment + charcoal.

   Accessibility contract:
   - never depend on red/green distinction
   - no flashing, pulsing, animated gradients, or blink states
   - color supplements labels/icons/shapes; it never owns meaning
   - subdued hover/pressed changes only
   ============================================================ */
QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #0B0F12;
    color: #E2E6E4;
}
QWidget { color: #E2E6E4; }

QWidget[foundryHeader="true"] {
    background-color: #10161A;
    border-bottom: 1px solid #5E5138;
}
QLabel[pageTitle="true"] {
    color: #D5A85F;
    font-family: "Montserrat";
    font-size: 21pt;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel[heroTitle="true"] { color: #E5E7E2; }
QLabel[pageSubtitle="true"], QLabel[heroSubtitle="true"] { color: #A8B1B3; }
QLabel[departmentLabel="true"] { color: #7EA6B8; }

QFrame[foundryCard="true"], QFrame[bookPanel="true"], QWidget[bookPanel="true"],
QFrame[rosterMetricCard="true"] {
    background-color: #141A1E;
    border: 1px solid #65563B;
    border-radius: 4px;
}
QWidget[cardHeader="true"] {
    background-color: #182126;
    border-bottom: 1px solid #465057;
}
QLabel[cardTitle="true"], QLabel[rosterMetricTitle="true"] {
    color: #C49A5A;
    font-weight: 700;
}
QLabel[cardIcon="true"], QLabel[rosterMetricIcon="true"] {
    color: #C8B58D;
}
QLabel[rosterMetricOrdinal="true"] {
    color: #C49A5A;
    border: 1px solid #65563B;
    border-radius: 12px;
    min-width: 22px;
    min-height: 22px;
}
QLabel[rosterMetricValue="true"] {
    color: #E2E6E4;
    font-size: 20px;
    font-weight: 700;
}

QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #C7B184;
    color: #28251F;
    border: 1px solid #88734B;
    border-radius: 3px;
}
QFrame[parchment="true"] QLabel, QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel, QWidget[foundryNoteCard="true"] QLabel {
    color: #28251F;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #10161A;
    color: #E2E6E4;
    selection-background-color: #334B5A;
    selection-color: #FFFFFF;
    border: 1px solid #556169;
    border-radius: 3px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    border: 2px solid #B79258;
}

QPushButton {
    background-color: #171E23;
    color: #DCE2E2;
    border: 1px solid #515D64;
    border-radius: 3px;
    padding: 5px 9px;
}
QPushButton:hover {
    background-color: #1C262C;
    border-color: #708F9D;
}
QPushButton:pressed {
    background-color: #11171B;
    border: 2px solid #B79258;
}
QPushButton:checked {
    background-color: #24343D;
    color: #FFFFFF;
    border: 1px solid #7EA6B8;
    border-bottom: 3px solid #7EA6B8;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #253640;
    color: #FFFFFF;
    border: 1px solid #7397A7;
    border-left: 4px solid #7EA6B8;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #33271E;
    color: #F0D3B3;
    border: 2px solid #C98245;
}
QPushButton:disabled {
    background-color: #15191C;
    color: #737D82;
    border-color: #343C41;
}

QToolButton[rotationIntentChoice="true"] {
    background-color: #171E23;
    color: #DCE2E2;
    border: 1px solid #53616A;
    border-radius: 4px;
    padding: 10px 8px 8px 8px;
}
QToolButton[rotationIntentChoice="true"]:hover {
    background-color: #253640;
    color: #F0F4F5;
    border-color: #92AAB5;
}
QToolButton[rotationIntentChoice="true"]:checked {
    background-color: #24343D;
    color: #FFFFFF;
    border-color: #92AAB5;
    border-bottom: 3px solid #AABAC2;
}

QFrame[rotationResultsShell="true"] {
    background-color: #0C1418;
    border: 1px solid #465057;
    border-radius: 4px;
}
QPushButton[rotationResultNav="true"] {
    background-color: #141C21;
    color: #AEB8BC;
    border: 1px solid #3D464C;
    border-radius: 3px;
    text-align: left;
    padding: 6px 14px;
}
QPushButton[rotationResultNav="true"]:hover {
    background-color: #223039;
    color: #EDF2F4;
    border-color: #819BA7;
}
QPushButton[rotationResultNav="true"]:checked {
    background-color: #24343D;
    color: #FFFFFF;
    border-color: #8EA6B2;
    border-bottom: 3px solid #AABAC2;
}
QLabel[rotationResultsLocked="true"] {
    color: #C9D2D5;
    font-family: "Montserrat";
    font-size: 10pt;
}

QPlainTextEdit[parchmentEditor="true"] {
    background-color: rgba(199, 177, 132, 0.82);
    color: #28251F;
    border: 1px solid #88734B;
    border-radius: 3px;
    padding: 10px;
    font-family: "Cormorant Garamond";
    font-size: 12pt;
}
QPlainTextEdit[parchmentEditor="true"]:focus {
    border: 2px solid #7B909B;
}

QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: #0C1114;
    border-right: 1px solid #495157;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #C3CDD0;
    background-color: transparent;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #151D22;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #223039;
    color: #FFFFFF;
    border: 1px solid #536A76;
    border-left: 4px solid #7EA6B8;
}

QTabWidget::pane {
    border: 1px solid #414B51;
    background-color: #11171B;
}
QTabBar::tab {
    background-color: #131A1F;
    color: #AEB8BC;
    border: 1px solid #3D464C;
    padding: 7px 12px;
}
QTabBar::tab:selected {
    background-color: #24343D;
    color: #FFFFFF;
    border-bottom: 3px solid #7EA6B8;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #101519;
    alternate-background-color: #161D21;
    color: #DDE3E3;
    gridline-color: #303A40;
    selection-background-color: #314956;
    selection-color: #FFFFFF;
    border: 1px solid #50595F;
}
QHeaderView::section {
    background-color: #182126;
    color: #D3C6A8;
    border-right: 1px solid #3B454B;
    border-bottom: 1px solid #65563B;
    padding: 5px 7px;
}

QProgressBar {
    background-color: #090D10;
    color: #E2E6E4;
    border: 1px solid #515B61;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #739CB0;
    border-radius: 2px;
}
QProgressBar[rosterMetricProgress="true"] {
    min-height: 8px;
    max-height: 8px;
}

/* Semantic roles: blue=confirmed/safe, orange=blocked, gold=partial,
   lavender=review. Text/icon/shape must accompany every state. */
QLabel[successText="true"], QLabel[integrationState="true"] { color: #82B6D1; }
QLabel[criticalText="true"] { color: #D28A51; }
QLabel[warningText="true"] { color: #C6A85A; }
QLabel[specialText="true"] { color: #A89BC8; }
QLabel[neutralText="true"] { color: #A8B1B3; }

QLabel[raidSnapshotValue="true"] {
    color: #DDE3E3;
    font-size: 16px;
    font-weight: 600;
}
QLabel[evidencePlanned="true"] { color: #C6A85A; }
QLabel[evidenceManual="true"] { color: #82B6D1; }
QLabel[evidenceObserved="true"] { color: #A89BC8; }
QLabel[evidenceReview="true"] { color: #A8B1B3; }

QScrollBar:vertical, QScrollBar:horizontal { background: #0B0F12; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #465159;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #596770;
}
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
    """Apply the single Urban Wilderness skin and safe semantic palette."""

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
        return VISUAL_THEME_URBAN_WILDERNESS

    def color_vision_mode(self) -> str:
        return COLOR_VISION_FRIENDLY

    def set_visual_theme(self, value: str) -> str:
        return self.preferences.set_visual_theme(VISUAL_THEME_URBAN_WILDERNESS)

    def set_color_vision_mode(self, value: str) -> str:
        return self.preferences.set_color_vision_mode(COLOR_VISION_FRIENDLY)

    def stylesheet_for_preferences(self) -> str:
        return load_grimoire_stylesheet() + "\n" + URBAN_WILDERNESS_OVERRIDES

    def apply(self, app: QApplication) -> None:
        app.setStyle("Fusion")
        qss = self.stylesheet_for_preferences()
        if qss:
            app.setStyleSheet(qss)

        logo = get_resource_path("bff.ico")
        if logo.exists():
            app.setWindowIcon(QIcon(str(logo)))

        app.setProperty("visualTheme", VISUAL_THEME_URBAN_WILDERNESS)
        app.setProperty("colorVisionMode", COLOR_VISION_FRIENDLY)
        app.setProperty("reducedMotion", True)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme

    @property
    def name(self):
        return "Urban Wilderness"

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
