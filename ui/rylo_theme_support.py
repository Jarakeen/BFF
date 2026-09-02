from __future__ import annotations

"""Rylo Midnight Ops visual skin and Settings integration.

The persisted ``rylo_grayscale`` preference key stays stable for compatibility,
but the presentation is deliberately non-fantasy: matte slate/concrete, chunky
controls, silver SVGs, and colorblind-safe semantic states.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


RYLO_MIDNIGHT_OVERRIDES = r"""
/* ============================================================
   RYLO — MIDNIGHT OPS / TACTICAL SLATE
   Matte concrete, worn steel, low-noise night operations.
   Default semantics are colorblind-safe:
   blue=safe, orange=danger, gold=warning, purple=special, gray=neutral.
   ============================================================ */

QMainWindow, QDialog, QScrollArea, QStackedWidget,
QScrollArea > QWidget > QWidget, QStackedWidget > QWidget {
    background-color: #0B0F13;
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    color: #D8E0E7;
}

QWidget {
    color: #D8E0E7;
    font-family: "Segoe UI", "Montserrat", Arial;
}

/* ---------- Page hierarchy: utilitarian, not fantasy ---------- */
QWidget[foundryHeader="true"] {
    background-color: rgba(14, 19, 24, 238);
    background-image: none;
    border: none;
    border-bottom: 2px solid #343E48;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] {
    color: #E2E7EC;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold", Arial;
    font-weight: 700;
    font-style: normal;
}
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"],
QLabel[heroSubtitle="true"], QLabel[muted="true"] {
    color: #9AA5B0;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QLabel[sidebarLogo="true"], QLabel[sidebarOffice="true"], QLabel[sidebarHeading="true"] {
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold", Arial;
    font-style: normal;
}
QLabel[sidebarLogo="true"] { color: #D3DAE1; }
QLabel[sidebarOffice="true"], QLabel[sidebarHeading="true"] { color: #909BA6; }

/* ---------- Chunky matte panels ---------- */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #151B21;
    background-image: none;
    border-left: 2px solid #3A444E;
    border-top: 2px solid #3A444E;
    border-right: 2px solid #20272E;
    border-bottom: 2px solid #20272E;
    border-radius: 1px;
}
QWidget[cardHeader="true"] {
    background-color: #1B2229;
    background-image: none;
    border: none;
    border-bottom: 2px solid #303A44;
    min-height: 30px;
}
QWidget[cardBody="true"] {
    background: transparent;
    border: none;
}
QLabel[cardTitle="true"] {
    color: #CAD2DA;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QLabel[cardIcon="true"] { color: #AEB7C1; }
QLabel[cardBadge="true"] {
    background-color: #10151A;
    color: #B6C0CA;
    border: 1px solid #46515C;
    border-radius: 2px;
    padding: 1px 6px;
}

/* Anything that used to be parchment becomes a raised equipment panel. */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #1A2026;
    background-image: none;
    color: #D8E0E7;
    border-left: 2px solid #404A54;
    border-top: 2px solid #404A54;
    border-right: 2px solid #222A31;
    border-bottom: 2px solid #222A31;
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
    color: #D8E0E7;
    font-family: "Segoe UI", "Montserrat", Arial;
    font-style: normal;
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #D7DEE5;
}

/* ---------- Controls: chunky, quiet, readable ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #10151A;
    background-image: none;
    color: #D8E0E7;
    selection-background-color: #245A86;
    selection-color: #FFFFFF;
    border-left: 2px solid #252D35;
    border-top: 2px solid #252D35;
    border-right: 2px solid #4B5661;
    border-bottom: 2px solid #4B5661;
    border-radius: 1px;
    padding: 4px 7px;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover {
    border-right-color: #65717D;
    border-bottom-color: #65717D;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #151C23;
    border: 2px solid #4EA3FF;
}
QComboBox QAbstractItemView {
    background-color: #10151A;
    color: #D8E0E7;
    selection-background-color: #244C70;
    selection-color: #FFFFFF;
    border: 2px solid #46515C;
}

QPushButton {
    background-color: #1A2026;
    background-image: none;
    color: #D2D9E0;
    border-left: 2px solid #46515C;
    border-top: 2px solid #46515C;
    border-right: 2px solid #252C33;
    border-bottom: 2px solid #252C33;
    border-radius: 1px;
    padding: 5px 10px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #222A32;
    border-left-color: #65717D;
    border-top-color: #65717D;
}
QPushButton:pressed {
    background-color: #11171D;
    border: 2px solid #4EA3FF;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #173A55;
    color: #FFFFFF;
    border: 2px solid #4EA3FF;
}
QPushButton[primary="true"]:hover, QPushButton[variant="primary"]:hover {
    background-color: #1C486A;
    border-color: #7AB9F4;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3A2413;
    color: #FFE2C4;
    border: 2px solid #F28C28;
}

/* ---------- Sidebar / navigation ---------- */
QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: rgba(9, 12, 15, 246);
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    border: none;
    border-right: 2px solid #343E48;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #AEB7C1;
    background-color: rgba(17, 22, 27, 185);
    border: 1px solid #242C33;
    border-radius: 1px;
    text-align: left;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #202830;
    color: #D7DEE5;
    border-color: #4B5661;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #17344A;
    color: #FFFFFF;
    border: 1px solid #3B688B;
    border-left: 4px solid #4EA3FF;
}

/* ---------- Tabs / lists / tables ---------- */
QTabWidget::pane {
    border: 2px solid #343E48;
    background-color: #11171C;
}
QTabBar::tab {
    background-color: #171D23;
    color: #98A3AE;
    border: 1px solid #303A44;
    padding: 6px 11px;
}
QTabBar::tab:selected {
    background-color: #17344A;
    color: #FFFFFF;
    border: 2px solid #4EA3FF;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #10151A;
    alternate-background-color: #171D23;
    color: #D8E0E7;
    gridline-color: #313A43;
    selection-background-color: #244C70;
    selection-color: #FFFFFF;
    border: 2px solid #343E48;
}
QHeaderView::section {
    background-color: #20272E;
    color: #C1CAD3;
    border: none;
    border-right: 1px solid #3B454F;
    border-bottom: 2px solid #4A5560;
    padding: 5px 7px;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QAbstractItemView::item { padding: 4px 6px; }

QCheckBox, QRadioButton {
    color: #D2D9E0;
    spacing: 7px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px;
    height: 15px;
}
QCheckBox::indicator:unchecked {
    background-color: #0D1217;
    border: 2px solid #596570;
}
QCheckBox::indicator:checked {
    background-color: #1D5D8C;
    border: 2px solid #4EA3FF;
}

QProgressBar {
    background-color: #0F1419;
    color: #D8E0E7;
    border: 2px solid #343E48;
    text-align: center;
}
QProgressBar::chunk { background-color: #327FBC; }

QScrollBar:vertical, QScrollBar:horizontal { background: #0A0E12; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #3E4852;
    min-height: 26px;
    min-width: 26px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #596570; }

QToolTip {
    background-color: #1B2229;
    color: #E2E7EC;
    border: 2px solid #596570;
}

/* ---------- Colorblind-safe semantic system ---------- */
QLabel[successText="true"], QLabel[integrationState="true"] { color: #4EA3FF; }
QLabel[criticalText="true"] { color: #F28C28; }
QLabel[warningText="true"] { color: #D9B21F; }
QLabel[specialText="true"] { color: #B388EB; }
QLabel[neutralText="true"] { color: #8A939D; }
QLabel[timerValue="true"] {
    color: #DCE4EB;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold", Arial;
}
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: #11171C;
    background-image: none;
    border: 2px solid #3C4650;
    color: #8D98A3;
    font-family: "Segoe UI", "Montserrat", Arial;
}
"""


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager

    # Keep the persisted key stable, but present the evolved identity to users.
    theme_manager.VISUAL_THEME_LABELS[VISUAL_THEME_RYLO] = "Rylo Midnight Ops"

    original_stylesheet_for_preferences = theme_manager.ThemeManager.stylesheet_for_preferences

    def stylesheet_with_midnight(self) -> str:
        qss = original_stylesheet_for_preferences(self)
        if self.visual_theme() == VISUAL_THEME_RYLO:
            asset_dir = get_resource_path("assets", "themes", "bff", "grimoire", "assets").as_posix()
            qss += "\n" + RYLO_MIDNIGHT_OVERRIDES.replace("@RYLO_ASSET_PATH@", asset_dir)
        return qss

    theme_manager.ThemeManager.stylesheet_for_preferences = stylesheet_with_midnight

    # SettingsPage currently has an Appearance placeholder. Replace only that
    # builder and preserve all unrelated settings behavior.
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
            "Foundry Grimoire keeps the field-journal identity. Rylo Midnight Ops uses matte "
            "slate/concrete, chunky equipment-panel controls, silver icons, and low-noise night-ops contrast."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        accessibility = QLabel(
            "Rylo defaults to colorblind-safe status colors: blue = safe, orange = danger, "
            "gold = warning, purple = special, gray = neutral. Color is never intended to be the only cue."
        )
        accessibility.setWordWrap(True)
        accessibility.setProperty("muted", True)
        layout.addWidget(accessibility)

        rylo_note = QLabel(
            "RYLO / MIDNIGHT OPS  ·  matte · tactical · low-glare · performance-first"
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
