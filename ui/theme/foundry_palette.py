from __future__ import annotations

from PySide6.QtWidgets import QApplication


# Foundry palette requested for the current UI redesign.
DEEP_TEAL = "#14282C"
TEAL = "#1D3A3F"
DEEP_WINE = "#2C1424"
PLUM = "#3F1D33"
OLIVE = "#3F391D"
PARCHMENT = "#E5D99E"

MUTED_TEXT = PARCHMENT
DIM_TEXT = "#C9C080"
GRID = OLIVE


PALETTE_OVERRIDE = f"""
/* ==========================================================
   BLACK FEATHER FOUNDRY - Teal / Plum / Olive Palette
   ========================================================== */

/* ----------------------------------------------------------
   Global surfaces
   ---------------------------------------------------------- */

QWidget {{
    background-color: {DEEP_TEAL};
    color: {PARCHMENT};
}}

QMainWindow,
QScrollArea,
QScrollArea > QWidget > QWidget {{
    background-color: {DEEP_TEAL};
}}

#sidebar {{
    background-color: {DEEP_TEAL};
    border-right: 1px solid {OLIVE};
}}

/* ----------------------------------------------------------
   Typography
   ---------------------------------------------------------- */

QLabel,
QCheckBox,
QRadioButton {{
    color: {PARCHMENT};
}}

#brandMark,
#brandSubtitle,
#pageSubtitle,
QLabel[section="true"],
QLabel[cardIcon="true"],
QLabel[cardTitle="true"],
#brandTitle,
#pageTitle {{
    color: {PARCHMENT};
}}

#statusLabel {{
    background-color: {DEEP_TEAL};
    border-top-color: {OLIVE};
    color: {DIM_TEXT};
}}

/* ----------------------------------------------------------
   Cards
   ---------------------------------------------------------- */

QGroupBox,
QFrame[foundryCard="true"] {{
    background-color: {DEEP_TEAL};
    border-color: {OLIVE};
}}

QGroupBox::title {{
    background-color: {DEEP_TEAL};
    color: {PARCHMENT};
}}

QWidget[cardHeader="true"] {{
    background-color: {DEEP_WINE};
    border-bottom-color: {OLIVE};
}}

QWidget[cardBody="true"] {{
    background-color: {DEEP_TEAL};
}}

/* ----------------------------------------------------------
   Inputs / form controls
   ---------------------------------------------------------- */

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox {{
    background-color: {TEAL};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QLineEdit:hover,
QTextEdit:hover,
QPlainTextEdit:hover,
QComboBox:hover,
QComboBox:focus {{
    background-color: {TEAL};
    border-color: {PLUM};
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    background-color: {TEAL};
    border-color: {PLUM};
}}

QComboBox QAbstractItemView {{
    background-color: {TEAL};
    border-color: {OLIVE};
    color: {PARCHMENT};
    selection-background-color: {PLUM};
    selection-color: {PARCHMENT};
}}

/* ----------------------------------------------------------
   Navigation / buttons / effects
   ---------------------------------------------------------- */

QPushButton[nav="true"] {{
    color: {PARCHMENT};
    border-color: transparent;
}}

QPushButton[nav="true"]:hover,
QPushButton[nav="true"]:checked {{
    background-color: {PLUM};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QPushButton {{
    background-color: {TEAL};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QPushButton:hover {{
    background-color: {PLUM};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QPushButton:pressed,
QPushButton[primary="true"] {{
    background-color: {PLUM};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QTabWidget::pane {{
    background-color: {DEEP_TEAL};
    border-color: {OLIVE};
}}

QTabBar::tab {{
    background-color: {DEEP_TEAL};
    border-color: {OLIVE};
    color: {DIM_TEXT};
}}

QTabBar::tab:hover,
QTabBar::tab:selected {{
    background-color: {PLUM};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

/* ----------------------------------------------------------
   Tables / lists
   ---------------------------------------------------------- */

QTableWidget,
QTableView,
QListWidget,
QTreeWidget {{
    background-color: {TEAL};
    alternate-background-color: {TEAL};
    border-color: {OLIVE};
    color: {PARCHMENT};
    gridline-color: {OLIVE};
    selection-background-color: {PLUM};
    selection-color: {PARCHMENT};
}}

QHeaderView::section {{
    background-color: {TEAL};
    border-right-color: {OLIVE};
    border-bottom-color: {OLIVE};
    color: {PARCHMENT};
}}

QListWidget::item:hover,
QListWidget::item:selected {{
    background-color: {PLUM};
    color: {PARCHMENT};
}}

/* ----------------------------------------------------------
   Flush table cards
   ---------------------------------------------------------- */

QFrame[foundryCard="true"][tableCard="true"] {{
    background-color: {DEEP_TEAL};
    border-color: {OLIVE};
}}

QFrame[foundryCard="true"][tableCard="true"] QWidget[tableCardBody="true"] {{
    background-color: {TEAL};
}}

QFrame[foundryCard="true"][tableCard="true"] QTableWidget,
QFrame[foundryCard="true"][tableCard="true"] QTableView {{
    background-color: {TEAL};
    border: none;
    border-top: 1px solid {OLIVE};
    border-radius: 0px;
}}

/* ----------------------------------------------------------
   Progress / tooltips
   ---------------------------------------------------------- */

QProgressBar {{
    background-color: {TEAL};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

QProgressBar::chunk {{
    background-color: {PLUM};
}}

QToolTip {{
    background-color: {DEEP_WINE};
    border-color: {OLIVE};
    color: {PARCHMENT};
}}

/* ----------------------------------------------------------
   Scrollbars
   ---------------------------------------------------------- */

QScrollBar:vertical {{
    background: {DEEP_TEAL};
    width: 8px;
}}

QScrollBar::handle:vertical {{
    background: {TEAL};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {PLUM};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {DEEP_TEAL};
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {TEAL};
    min-width: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {PLUM};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def apply_foundry_palette(app: QApplication) -> None:
    """Apply the current Foundry palette without replacing the base theme."""
    app.setStyleSheet(app.styleSheet() + PALETTE_OVERRIDE)
