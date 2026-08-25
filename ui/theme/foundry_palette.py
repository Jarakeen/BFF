from __future__ import annotations

from PySide6.QtWidgets import QApplication


# Foundry palette requested for the current UI redesign.
DEEP_TEAL = "#14282C"
TEAL = "#1D3A3F"
DEEP_WINE = "#2C1424"
PLUM = "#3F1D33"
OLIVE = "#3F391D"
PARCHMENT = "#E5D99E"

MUTED_TEXT = "#A7ADA3"
DIM_TEXT = "#7F8D89"
GRID = "#2A3D3D"


PALETTE_OVERRIDE = f"""
/* ==========================================================
   BLACK FEATHER FOUNDRY - Teal / Plum Palette
   ========================================================== */

QWidget {{
    background-color: {DEEP_TEAL};
    color: {MUTED_TEXT};
}}

QMainWindow,
QScrollArea,
QScrollArea > QWidget > QWidget {{
    background-color: {DEEP_TEAL};
}}

#sidebar {{
    background-color: {DEEP_TEAL};
    border-right: 1px solid {TEAL};
}}

#brandMark,
#brandSubtitle,
#pageSubtitle,
QLabel[section="true"],
QLabel[cardIcon="true"],
QLabel[cardTitle="true"] {{
    color: {PARCHMENT};
}}

#brandTitle,
#pageTitle {{
    color: {PARCHMENT};
}}

#reminder,
QGroupBox,
QTabWidget::pane {{
    background-color: {PLUM};
    border-color: {TEAL};
}}

#statusLabel {{
    background-color: {DEEP_TEAL};
    border-top-color: {TEAL};
    color: {DIM_TEXT};
}}

QPushButton[nav="true"] {{
    color: {MUTED_TEXT};
}}

QPushButton[nav="true"]:hover {{
    background-color: {TEAL};
    border-color: {PARCHMENT};
    color: {PARCHMENT};
}}

QPushButton[nav="true"]:checked {{
    background-color: {PLUM};
    border-color: {PARCHMENT};
    color: {PARCHMENT};
}}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox {{
    background-color: {DEEP_WINE};
    border-color: {TEAL};
    color: {PARCHMENT};
}}

QLineEdit:hover,
QTextEdit:hover,
QPlainTextEdit:hover,
QComboBox:hover,
QComboBox:focus {{
    border-color: {PARCHMENT};
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    background-color: {PLUM};
    border-color: {PARCHMENT};
}}

QComboBox QAbstractItemView {{
    background-color: {DEEP_WINE};
    border-color: {TEAL};
    color: {PARCHMENT};
    selection-background-color: {TEAL};
    selection-color: {PARCHMENT};
}}

QPushButton {{
    background-color: {PLUM};
    border-color: {TEAL};
    color: {PARCHMENT};
}}

QPushButton:hover {{
    background-color: {TEAL};
    border-color: {PARCHMENT};
    color: {PARCHMENT};
}}

QPushButton:pressed,
QPushButton[primary="true"] {{
    background-color: {DEEP_WINE};
    border-color: {PARCHMENT};
    color: {PARCHMENT};
}}

QTabBar::tab {{
    background-color: {DEEP_TEAL};
    border-color: {TEAL};
    color: {DIM_TEXT};
}}

QTabBar::tab:hover,
QTabBar::tab:selected {{
    background-color: {PLUM};
    border-color: {PARCHMENT};
    color: {PARCHMENT};
}}

QTableWidget,
QTableView,
QListWidget,
QTreeWidget {{
    background-color: {DEEP_WINE};
    alternate-background-color: {PLUM};
    border-color: {TEAL};
    color: {MUTED_TEXT};
    gridline-color: {GRID};
    selection-background-color: {TEAL};
    selection-color: {PARCHMENT};
}}

QHeaderView::section {{
    background-color: {TEAL};
    border-right-color: {DEEP_TEAL};
    border-bottom-color: {DEEP_TEAL};
    color: {PARCHMENT};
}}

QListWidget::item:selected {{
    background-color: {TEAL};
    color: {PARCHMENT};
}}

QProgressBar {{
    background-color: {DEEP_WINE};
    border-color: {TEAL};
    color: {PARCHMENT};
}}

QProgressBar::chunk {{
    background-color: {OLIVE};
}}

QToolTip {{
    background-color: {DEEP_WINE};
    border-color: {TEAL};
    color: {PARCHMENT};
}}

QFrame[foundryCard="true"] {{
    background-color: {TEAL};
    border-color: {PLUM};
}}

QWidget[cardHeader="true"] {{
    background-color: {DEEP_TEAL};
    border-bottom-color: {PLUM};
}}

QWidget[cardBody="true"] {{
    background-color: {TEAL};
}}

QFrame[foundryCard="true"][tableCard="true"] {{
    background-color: {TEAL};
    border-color: {PLUM};
}}

QFrame[foundryCard="true"][tableCard="true"] QWidget[tableCardBody="true"] {{
    background-color: {DEEP_WINE};
}}

QFrame[foundryCard="true"][tableCard="true"] QTableWidget,
QFrame[foundryCard="true"][tableCard="true"] QTableView {{
    border: none;
    border-top: 1px solid {PLUM};
    border-radius: 0px;
}}

QScrollBar:vertical {{
    background: {DEEP_TEAL};
    width: 8px;
}}

QScrollBar::handle:vertical {{
    background: {PLUM};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEAL};
}}

QScrollBar:horizontal {{
    background: {DEEP_TEAL};
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {PLUM};
    min-width: 28px;
    border-radius: 4px;
}}
"""


def apply_foundry_palette(app: QApplication) -> None:
    """Apply the current Foundry palette without replacing the base theme."""
    app.setStyleSheet(app.styleSheet() + PALETTE_OVERRIDE)
