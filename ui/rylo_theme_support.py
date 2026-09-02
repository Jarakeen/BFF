from __future__ import annotations

"""Rylo Midnight Operations visual skin and Settings integration.

This keeps the existing persisted ``rylo_grayscale`` preference key for backward
compatibility while replacing the old grayscale/crimson presentation with a
clean midnight operations console: obsidian, gunmetal, cold steel, ice blue,
and restrained cyan telemetry accents.
"""

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from services.accessibility_preferences import VISUAL_THEME_FOUNDRY, VISUAL_THEME_RYLO

_INSTALLED = False


RYLO_MIDNIGHT_OVERRIDES = r"""
/* ============================================================
   RYLO — MIDNIGHT OPERATIONS CONSOLE
   Precision, telemetry, restrained night-ops instrumentation.
   ============================================================ */
QWidget {
    background-color: #0A0D12;
    color: #E7EBF0;
}
QMainWindow, QDialog, QScrollArea,
QScrollArea > QWidget > QWidget {
    background-color: #0A0D12;
}

QWidget[foundryHeader="true"] {
    background-color: #0C1118;
    border-bottom: 1px solid #263445;
}
QLabel[pageTitle="true"], QLabel[heroTitle="true"] {
    color: #F1F4F7;
}
QLabel[pageSubtitle="true"], QLabel[departmentLabel="true"],
QLabel[heroSubtitle="true"], QLabel[muted="true"] {
    color: #8EA0B5;
}

QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #10161E;
    background-image: none;
    border: 1px solid #263445;
}
QWidget[cardHeader="true"] {
    background-color: #151D27;
    border-bottom: 1px solid #314258;
}
QLabel[cardTitle="true"] {
    color: #DCE5EE;
}
QLabel[cardIcon="true"] {
    color: #8EA0B5;
}
QLabel[cardBadge="true"] {
    background-color: #111A24;
    color: #9FC5EE;
    border: 1px solid #38536F;
}

QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #111820;
    background-image: none;
    color: #E7EBF0;
    border: 1px solid #304155;
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel,
QWidget[foundryNoteCard="true"] QLabel,
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit,
QFrame[foundryNoteCard="true"] QPlainTextEdit,
QFrame[foundryNoteCard="true"] QTextEdit {
    color: #E7EBF0;
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #DCE5EE;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #0D131B;
    color: #E7EBF0;
    selection-background-color: #294F73;
    selection-color: #FFFFFF;
    border: 1px solid #314258;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover {
    border-color: #46617D;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #111A24;
    border: 1px solid #5FA8FF;
}
QComboBox QAbstractItemView {
    background-color: #0D131B;
    color: #E7EBF0;
    selection-background-color: #203A54;
    selection-color: #FFFFFF;
    border: 1px solid #314258;
}

QPushButton {
    background-color: #141C26;
    color: #DCE5EE;
    border: 1px solid #34485E;
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #1A2734;
    border-color: #5B7898;
}
QPushButton:pressed {
    background-color: #0F1720;
    border-color: #5FA8FF;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #17314A;
    color: #F4F8FC;
    border: 1px solid #5FA8FF;
}
QPushButton[primary="true"]:hover, QPushButton[variant="primary"]:hover {
    background-color: #1D4160;
    border-color: #7BBAFF;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #26161A;
    color: #F1CED1;
    border: 1px solid #B94A52;
}

QWidget[foundrySidebar="true"], QFrame[settingsRail="true"] {
    background-color: #090D12;
    border-color: #263445;
}
QPushButton[nav="true"], QPushButton[settingsNav="true"] {
    color: #AEBCCB;
    background-color: transparent;
    border: 1px solid transparent;
}
QPushButton[nav="true"]:hover, QPushButton[settingsNav="true"]:hover {
    background-color: #121B25;
    border-color: #293B4E;
}
QPushButton[nav="true"]:checked, QPushButton[settingsNav="true"]:checked {
    background-color: #14283A;
    color: #FFFFFF;
    border: 1px solid #335B7E;
    border-left: 2px solid #5FA8FF;
}

QTabWidget::pane {
    border: 1px solid #314258;
    background-color: #0D131B;
}
QTabBar::tab {
    background-color: #101720;
    color: #8EA0B5;
    border: 1px solid #29394C;
    padding: 6px 10px;
}
QTabBar::tab:selected {
    background-color: #17314A;
    color: #F4F8FC;
    border-color: #5FA8FF;
}

QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: #0C1219;
    alternate-background-color: #111923;
    color: #DCE5EE;
    gridline-color: #263445;
    selection-background-color: #1C3B55;
    selection-color: #FFFFFF;
    border: 1px solid #263445;
}
QHeaderView::section {
    background-color: #151E29;
    color: #AFC0D0;
    border-right: 1px solid #2B3D50;
    border-bottom: 1px solid #3B526A;
    padding: 5px;
}

QCheckBox, QRadioButton {
    color: #DCE5EE;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 14px;
    height: 14px;
}
QCheckBox::indicator:unchecked {
    background-color: #0C1219;
    border: 1px solid #52667C;
}
QCheckBox::indicator:checked {
    background-color: #2C6EA3;
    border: 1px solid #7BBAFF;
}

QProgressBar {
    background-color: #0C1219;
    color: #E7EBF0;
    border: 1px solid #314258;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #4E91D1;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: #090D12;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #34485E;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #4B6682;
}

QToolTip {
    background-color: #151E29;
    color: #E7EBF0;
    border: 1px solid #46617D;
}

QLabel[successText="true"], QLabel[integrationState="true"] {
    color: #55D6D0;
}
QLabel[warningText="true"] {
    color: #D7B563;
}
QLabel[criticalText="true"] {
    color: #D36B73;
}
QLabel[timerValue="true"] {
    color: #9BC9FF;
}
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: #0D141D;
    border: 1px solid #31485E;
    color: #8296AA;
}
"""


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager

    # Keep the persisted key stable, but present the new identity to users.
    theme_manager.VISUAL_THEME_LABELS[VISUAL_THEME_RYLO] = "Rylo Midnight Operations"

    original_stylesheet_for_preferences = theme_manager.ThemeManager.stylesheet_for_preferences

    def stylesheet_with_midnight(self) -> str:
        qss = original_stylesheet_for_preferences(self)
        if self.visual_theme() == VISUAL_THEME_RYLO:
            qss += "\n" + RYLO_MIDNIGHT_OVERRIDES
        return qss

    theme_manager.ThemeManager.stylesheet_for_preferences = stylesheet_with_midnight

    # SettingsPage currently has an Appearance placeholder. Replace only that
    # builder and preserve all unrelated settings behavior.
    from ui import settings_page

    original_appearance_page = settings_page.SettingsPage._appearance_page
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
            "Foundry Grimoire keeps the field-journal identity. Rylo Midnight Operations uses "
            "obsidian, gunmetal, cold steel, ice-blue focus states, and restrained cyan telemetry."
        )
        description.setWordWrap(True)
        description.setProperty("muted", True)
        layout.addWidget(description)

        rylo_note = QLabel(
            "RYLO / MIDNIGHT OPERATIONS  ·  compact, precise, low-noise, performance-first"
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
            self.status.success(
                "Visual theme: " + self.visual_theme_combo.currentText() + "."
            )

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
