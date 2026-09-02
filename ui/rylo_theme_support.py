from __future__ import annotations

"""Rylo visual skin and Settings integration.

The persisted ``rylo_grayscale`` preference key stays stable for compatibility,
but the presentation is intentionally urban rather than military: matte city
stone, weathered steel, restrained brick-red identity accents, and a separate
colorblind-safe semantic palette for status meaning.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


RYLO_URBAN_OVERRIDES = r"""
/* ============================================================
   RYLO — GUARDIAN / CITY AFTER MIDNIGHT

   Identity: black concrete, worn steel, muted brick red,
   restrained old-gold details. No glossy surfaces or neon.

   Semantic meaning remains independent of branding:
   blue=safe, orange=danger, gold=warning,
   purple=special, gray=neutral.
   ============================================================ */

QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #0B0B0D;
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    color: #D0D3D5;
}

QWidget {
    color: #D0D3D5;
    font-family: "Segoe UI", "Montserrat", Arial;
}

/* ---------- Headers: city signage, not fantasy ornament ---------- */
QWidget[foundryHeader="true"] {
    background-color: rgba(14, 14, 16, 242);
    background-image: none;
    border: none;
    border-bottom: 2px solid #34363A;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] {
    color: #E0E0DE;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    font-style: normal;
    letter-spacing: 1px;
}
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"],
QLabel[heroSubtitle="true"], QLabel[muted="true"] {
    color: #969A9E;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QLabel[departmentLabel="true"] {
    color: #9C6F70;
    font-weight: 600;
}

QLabel[sidebarLogo="true"], QLabel[sidebarOffice="true"], QLabel[sidebarHeading="true"] {
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-style: normal;
}
QLabel[sidebarLogo="true"] {
    color: #D5D3CF;
    letter-spacing: 1px;
}
QLabel[sidebarOffice="true"] {
    color: #8B1E24;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel[sidebarHeading="true"] {
    color: #B8B3AB;
    font-size: 9px;
    font-weight: 700;
}
QLabel[sidebarMeta="true"], QLabel[sidebarFooter="true"] {
    color: #858A8E;
}

/* ---------- Matte city panels ---------- */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #151618;
    background-image: none;
    border-left: 2px solid #3B3D40;
    border-top: 2px solid #3B3D40;
    border-right: 2px solid #222326;
    border-bottom: 2px solid #222326;
    border-radius: 1px;
}
QWidget[cardHeader="true"] {
    background-color: #1B1C1F;
    background-image: none;
    border: none;
    border-bottom: 2px solid #34363A;
    min-height: 30px;
}
QWidget[cardBody="true"] {
    background: transparent;
    border: none;
}
QLabel[cardTitle="true"] {
    color: #D0CECA;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel[cardIcon="true"] { color: #A8ADB1; }
QLabel[cardBadge="true"] {
    background-color: #101113;
    color: #BABDC0;
    border: 1px solid #4A4C50;
    border-radius: 2px;
    padding: 1px 6px;
}

/* Parchment surfaces become raised concrete/steel note plates. */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #1A1B1D;
    background-image: none;
    color: #D2D0CC;
    border-left: 2px solid #44464A;
    border-top: 2px solid #44464A;
    border-right: 2px solid #25272A;
    border-bottom: 2px solid #25272A;
    border-radius: 1px;
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel,
QWidget[foundryNoteCard="true"] QLabel,
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit,
QFrame[foundryNoteCard="true"] QPlainTextEdit,
QFrame[foundryNoteCard="true"] QTextEdit {
    color: #D2D0CC;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #D7D3CC;
}

/* ---------- Controls: heavy enough to feel physical, never shiny ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #101113;
    background-image: none;
    color: #D5D6D7;
    selection-background-color: #3A454F;
    selection-color: #FFFFFF;
    border-left: 2px solid #282A2D;
    border-top: 2px solid #282A2D;
    border-right: 2px solid #505359;
    border-bottom: 2px solid #505359;
    border-radius: 1px;
    padding: 4px 7px;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover {
    border-right-color: #696C70;
    border-bottom-color: #696C70;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #17181A;
    border: 2px solid #B88A3C;
}
QComboBox QAbstractItemView {
    background-color: #111214;
    color: #D5D6D7;
    selection-background-color: #34373B;
    selection-color: #FFFFFF;
    border: 2px solid #4B4E53;
}

QPushButton {
    background-color: #1A1B1D;
    background-image: none;
    color: #D0D1D2;
    border-left: 2px solid #46484C;
    border-top: 2px solid #46484C;
    border-right: 2px solid #26282B;
    border-bottom: 2px solid #26282B;
    border-radius: 1px;
    padding: 5px 10px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #242528;
    border-left-color: #66686C;
    border-top-color: #66686C;
}
QPushButton:pressed {
    background-color: #101113;
    border: 2px solid #B88A3C;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #2A1719;
    color: #F0ECE5;
    border-left: 3px solid #8B1E24;
    border-top: 2px solid #5B3336;
    border-right: 2px solid #211719;
    border-bottom: 2px solid #211719;
}
QPushButton[primary="true"]:hover, QPushButton[variant="primary"]:hover {
    background-color: #351B1E;
    border-left-color: #A52B31;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3A2413;
    color: #FFE2C4;
    border: 2px solid #F28C28;
}

/* ---------- Sidebar: neighborhood field office ---------- */
QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: rgba(8, 8, 10, 246);
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    border: none;
    border-right: 2px solid #34363A;
}
QLabel[sidebarBrandMark="true"] {
    background: transparent;
}
QFrame[sidebarDivider="true"] {
    color: #34363A;
    border-color: #34363A;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #AFB1B3;
    background-color: rgba(18, 18, 20, 190);
    border: 1px solid #292A2D;
    border-radius: 1px;
    text-align: left;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #232427;
    color: #E0DEDA;
    border-color: #4D4F53;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #281719;
    color: #F0ECE7;
    border-top: 1px solid #4C3436;
    border-right: 1px solid #302326;
    border-bottom: 1px solid #302326;
    border-left: 4px solid #8B1E24;
}
QPushButton[navCategoryHeader="true"] {
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    letter-spacing: 0.5px;
}

/* ---------- Tabs, lists, tables ---------- */
QTabWidget::pane {
    border: 2px solid #34363A;
    background-color: #111214;
}
QTabBar::tab {
    background-color: #18191B;
    color: #96999C;
    border: 1px solid #303236;
    padding: 6px 11px;
}
QTabBar::tab:selected {
    background-color: #261719;
    color: #F0ECE7;
    border-bottom: 3px solid #8B1E24;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #101113;
    alternate-background-color: #18191B;
    color: #D2D3D4;
    gridline-color: #323438;
    selection-background-color: #34373A;
    selection-color: #FFFFFF;
    border: 2px solid #34363A;
}
QHeaderView::section {
    background-color: #202124;
    color: #C6C4C0;
    border: none;
    border-right: 1px solid #3C3E42;
    border-bottom: 2px solid #4A4C50;
    padding: 5px 7px;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QAbstractItemView::item { padding: 4px 6px; }

QCheckBox, QRadioButton {
    color: #D0D1D2;
    spacing: 7px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px;
    height: 15px;
}
QCheckBox::indicator:unchecked {
    background-color: #0D0E10;
    border: 2px solid #5A5D61;
}
QCheckBox::indicator:checked {
    background-color: #404347;
    border: 2px solid #D0D2D4;
}

QProgressBar {
    background-color: #101113;
    color: #D0D1D2;
    border: 2px solid #34363A;
    text-align: center;
}
QProgressBar::chunk { background-color: #6B7075; }

QScrollBar:vertical, QScrollBar:horizontal { background: #090A0B; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #424448;
    min-height: 26px;
    min-width: 26px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #5C5F63; }

QToolTip {
    background-color: #1C1D20;
    color: #E0DEDA;
    border: 2px solid #5B5D61;
}

/* ---------- Colorblind-safe semantic layer ---------- */
QLabel[successText="true"], QLabel[integrationState="true"] { color: #4EA3FF; }
QLabel[criticalText="true"] { color: #F28C28; }
QLabel[warningText="true"] { color: #D9B21F; }
QLabel[specialText="true"] { color: #B388EB; }
QLabel[neutralText="true"] { color: #8A939D; }
QLabel[timerValue="true"] {
    color: #D9D7D2;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
}
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: #111214;
    background-image: none;
    border: 2px solid #3D3F43;
    color: #8E9296;
    font-family: "Segoe UI", "Montserrat", Arial;
}
"""


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager

    # Preserve the persisted key; only the user-facing identity changes.
    theme_manager.VISUAL_THEME_LABELS[VISUAL_THEME_RYLO] = "Rylo · Guardian After Dark"

    original_stylesheet_for_preferences = theme_manager.ThemeManager.stylesheet_for_preferences

    def stylesheet_with_rylo(self) -> str:
        qss = original_stylesheet_for_preferences(self)
        if self.visual_theme() == VISUAL_THEME_RYLO:
            asset_dir = get_resource_path(
                "assets", "themes", "bff", "grimoire", "assets"
            ).as_posix()
            qss += "\n" + RYLO_URBAN_OVERRIDES.replace("@RYLO_ASSET_PATH@", asset_dir)
        return qss

    theme_manager.ThemeManager.stylesheet_for_preferences = stylesheet_with_rylo

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
            "Foundry Grimoire keeps the field-journal identity. Rylo · Guardian After Dark "
            "uses matte city stone, worn steel, silver icons, muted brick-red branding, and "
            "subtle old-gold focus details."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        accessibility = QLabel(
            "Rylo keeps brand color separate from status meaning: blue = safe, orange = danger, "
            "gold = warning, purple = special, gray = neutral. Selection and focus also use "
            "shape, border weight, and contrast rather than color alone."
        )
        accessibility.setWordWrap(True)
        accessibility.setProperty("muted", True)
        layout.addWidget(accessibility)

        rylo_note = QLabel(
            "RYLO  ·  NIGHT · CITY · CONCRETE · LOYALTY · FAMILY · PROTECTION"
        )
        rylo_note.setWordWrap(True)
        rylo_note.setProperty("integrationState", True)
        layout.addWidget(rylo_note)

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

            self.status.success("Visual theme: " + self.visual_theme_combo.currentText() + ".")

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
