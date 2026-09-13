from __future__ import annotations

"""Rylo visual skin and Settings integration.

The persisted ``rylo_grayscale`` preference key stays stable for compatibility,
but the presentation is intentionally urban rather than military: warm charcoal,
weathered steel, silver iconography, and a colorblind-safe semantic accent set.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


RYLO_URBAN_OVERRIDES = r"""
/* ============================================================
   RYLO — GUARDIAN / CITY AFTER MIDNIGHT

   Identity: warm charcoal, soft black, weathered steel, silver.
   Branding is deliberately neutral so red/green deficiency never
   has to carry interface meaning.

   Semantic meaning remains independent of branding:
   blue=safe/primary, orange=danger, gold=warning/focus,
   purple=special, silver/gray=neutral.
   ============================================================ */

QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #121315;
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    color: #D4D1CB;
}

QWidget {
    color: #D4D1CB;
    font-family: "Segoe UI", "Montserrat", Arial;
}

/* ---------- Headers: quiet city signage ---------- */
QWidget[foundryHeader="true"] {
    background-color: rgba(23, 24, 26, 244);
    background-image: none;
    border: none;
    border-bottom: 1px solid #414347;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] {
    color: #E4E1DA;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    font-style: normal;
    letter-spacing: 1px;
}
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"],
QLabel[heroSubtitle="true"], QLabel[muted="true"] {
    color: #A29F9A;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QLabel[departmentLabel="true"] {
    color: #8FB6D9;
    font-weight: 600;
}

QLabel[sidebarLogo="true"], QLabel[sidebarOffice="true"], QLabel[sidebarHeading="true"] {
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-style: normal;
}
QLabel[sidebarLogo="true"] {
    color: #DAD7D1;
    letter-spacing: 1px;
}
QLabel[sidebarOffice="true"] {
    color: #BFC5CB;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel[sidebarHeading="true"] {
    color: #C2BEB7;
    font-size: 9px;
    font-weight: 700;
}
QLabel[sidebarMeta="true"], QLabel[sidebarFooter="true"] {
    color: #8D9093;
}

/* ---------- Warm charcoal city panels ---------- */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #202124;
    background-image: none;
    border: 1px solid #3C3E42;
    border-radius: 2px;
}
QWidget[cardHeader="true"] {
    background-color: #27282B;
    background-image: none;
    border: none;
    border-bottom: 1px solid #414347;
    min-height: 30px;
}
QWidget[cardBody="true"] {
    background: transparent;
    border: none;
}
QLabel[cardTitle="true"] {
    color: #D8D4CD;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel[cardIcon="true"] { color: #C4C9CE; }
QLabel[cardBadge="true"] {
    background-color: #18191B;
    color: #C5C8CB;
    border: 1px solid #4B4E52;
    border-radius: 2px;
    padding: 1px 6px;
}

/* Parchment surfaces become soft raised charcoal note plates. */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #26272A;
    background-image: none;
    color: #D8D4CD;
    border: 1px solid #45474B;
    border-radius: 2px;
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel,
QWidget[foundryNoteCard="true"] QLabel,
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit,
QFrame[foundryNoteCard="true"] QPlainTextEdit,
QFrame[foundryNoteCard="true"] QTextEdit {
    color: #D8D4CD;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #E0DCD4;
}

/* ---------- Controls: charcoal, silver, restrained accent ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #1A1B1E;
    background-image: none;
    color: #D9D7D2;
    selection-background-color: #36556F;
    selection-color: #FFFFFF;
    border: 1px solid #505257;
    border-radius: 2px;
    padding: 4px 7px;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover {
    border-color: #686B70;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #222326;
    border: 2px solid #C6A85B;
}
QComboBox QAbstractItemView {
    background-color: #1C1D20;
    color: #D9D7D2;
    selection-background-color: #35495B;
    selection-color: #FFFFFF;
    border: 1px solid #55585D;
}

QPushButton {
    background-color: #252629;
    background-image: none;
    color: #D5D3CE;
    border: 1px solid #4C4E52;
    border-radius: 2px;
    padding: 5px 10px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #303135;
    border-color: #66696E;
}
QPushButton:pressed {
    background-color: #1A1B1E;
    border: 2px solid #C6A85B;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #27323B;
    color: #F0EEE9;
    border: 1px solid #56738B;
    border-left: 3px solid #6FA8D3;
}
QPushButton[primary="true"]:hover, QPushButton[variant="primary"]:hover {
    background-color: #30404D;
    border-color: #78A9CF;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3A2C20;
    color: #FFE2C4;
    border: 2px solid #F28C28;
}

/* ---------- Sidebar: neighborhood field office ---------- */
QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: rgba(19, 20, 22, 247);
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    border: none;
    border-right: 1px solid #414347;
}
QLabel[sidebarBrandMark="true"] {
    background: transparent;
}
QFrame[sidebarDivider="true"] {
    color: #414347;
    border-color: #414347;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #BBBEC1;
    background-color: rgba(34, 35, 38, 205);
    border: 1px solid #35373A;
    border-radius: 2px;
    text-align: left;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #2D2F32;
    color: #E1DFDA;
    border-color: #52555A;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #29333C;
    color: #F0EEE9;
    border-top: 1px solid #46545F;
    border-right: 1px solid #39434B;
    border-bottom: 1px solid #39434B;
    border-left: 4px solid #6FA8D3;
}
QPushButton[navCategoryHeader="true"] {
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    letter-spacing: 0.5px;
}

/* ---------- Tabs, lists, tables ---------- */
QTabWidget::pane {
    border: 1px solid #414347;
    background-color: #1B1C1F;
}
QTabBar::tab {
    background-color: #252629;
    color: #A8A6A2;
    border: 1px solid #3D3F43;
    padding: 6px 11px;
}
QTabBar::tab:selected {
    background-color: #2B343D;
    color: #F0EEE9;
    border-bottom: 3px solid #6FA8D3;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #1A1B1E;
    alternate-background-color: #232427;
    color: #D6D4CF;
    gridline-color: #3C3E42;
    selection-background-color: #35495B;
    selection-color: #FFFFFF;
    border: 1px solid #414347;
}
QHeaderView::section {
    background-color: #292A2D;
    color: #CCC9C3;
    border: none;
    border-right: 1px solid #414347;
    border-bottom: 1px solid #505257;
    padding: 5px 7px;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QAbstractItemView::item { padding: 4px 6px; }

QCheckBox, QRadioButton {
    color: #D5D3CE;
    spacing: 7px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px;
    height: 15px;
}
QCheckBox::indicator:unchecked {
    background-color: #17181A;
    border: 2px solid #62656A;
}
QCheckBox::indicator:checked {
    background-color: #4A5966;
    border: 2px solid #D2D6DA;
}

QProgressBar {
    background-color: #1A1B1E;
    color: #D5D3CE;
    border: 1px solid #414347;
    text-align: center;
}
QProgressBar::chunk { background-color: #6F8293; }

QScrollBar:vertical, QScrollBar:horizontal { background: #151618; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #4B4D51;
    min-height: 26px;
    min-width: 26px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #65686D; }

QToolTip {
    background-color: #292A2D;
    color: #E2DFD9;
    border: 1px solid #62656A;
}

/* ---------- Colorblind-safe semantic layer ---------- */
QLabel[successText="true"], QLabel[integrationState="true"] { color: #6FB6F1; }
QLabel[criticalText="true"] { color: #F29B45; }
QLabel[warningText="true"] { color: #E0BE57; }
QLabel[specialText="true"] { color: #B99AE8; }
QLabel[neutralText="true"] { color: #9AA2AA; }
QLabel[timerValue="true"] {
    color: #DCD8D0;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
}
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: #202124;
    background-image: none;
    border: 1px solid #45474B;
    color: #989B9E;
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
            "uses warm charcoal, soft black, weathered steel, silver icons, and restrained "
            "colorblind-safe accents."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        accessibility = QLabel(
            "Rylo keeps branding neutral and status meaning explicit: blue = safe or primary, "
            "orange = danger, gold = warning or focus, purple = special, gray = neutral. "
            "Selection and focus also use shape, border weight, and contrast rather than color alone."
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