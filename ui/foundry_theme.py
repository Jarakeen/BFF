from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# Black Feather Foundry palette
# Background: #14282c
# Surface/table/input: #1d3a3f
# Card header: #2c1424
# Text: #e5d99e
# Hover/selection: #3f1d33
# Borders: #3f391d
# Scrollbars: #1d3a3f

FOUNDry_STYLESHEET = r"""
QWidget {
    background-color: #14282c;
    color: #e5d99e;
    font-family: "Segoe UI";
    font-size: 12px;
}

QMainWindow {
    background-color: #14282c;
}

#sidebar {
    background-color: #14282c;
    border-right: 1px solid #3f391d;
}

#brandMark {
    color: #e5d99e;
    font-size: 34px;
}

#brandTitle {
    color: #e5d99e;
    font-family: Georgia, "Times New Roman";
    font-size: 23px;
    font-weight: bold;
    letter-spacing: 1px;
}

#brandSubtitle,
#pageSubtitle {
    color: #e5d99e;
    font-family: Georgia, "Times New Roman";
    font-size: 11px;
}

#reminder {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
    border-radius: 4px;
    color: #e5d99e;
    padding: 9px;
}

#sidebarFooter,
#statusLabel {
    color: #e5d99e;
}

#statusLabel {
    background-color: #14282c;
    border-top: 1px solid #3f391d;
    padding: 5px 8px;
}

#pageTitle {
    background-color: transparent;
    color: #e5d99e;
    font-family: Georgia, "Times New Roman";
    font-size: 27px;
    font-weight: bold;
    padding: 2px 0px;
}

QPushButton[nav="true"] {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    color: #e5d99e;
    min-height: 31px;
    padding: 5px 10px;
    text-align: left;
}

QPushButton[nav="true"]:hover,
QPushButton[nav="true"]:checked {
    background-color: #3f1d33;
    border-color: #3f391d;
    color: #e5d99e;
}

QPushButton[nav="true"]:checked {
    font-weight: bold;
}

QGroupBox {
    background-color: #14282c;
    border: 1px solid #3f391d;
    border-radius: 5px;
    margin-top: 11px;
    padding: 11px 9px 8px 9px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0px 7px;
    color: #e5d99e;
    background-color: #14282c;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
    font-weight: bold;
}

QLabel {
    background-color: transparent;
    color: #e5d99e;
}

QLabel[section="true"],
QLabel[cardTitle="true"] {
    color: #e5d99e;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: bold;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
    border-radius: 3px;
    color: #e5d99e;
    padding: 5px 7px;
    selection-background-color: #3f1d33;
    selection-color: #e5d99e;
}

QLineEdit:hover,
QTextEdit:hover,
QPlainTextEdit:hover,
QComboBox:hover,
QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus {
    border-color: #3f1d33;
}

QComboBox {
    min-height: 26px;
}

QComboBox::drop-down {
    width: 24px;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
    color: #e5d99e;
    selection-background-color: #3f1d33;
    selection-color: #e5d99e;
    padding: 3px;
}

QCheckBox,
QRadioButton {
    background-color: transparent;
    color: #e5d99e;
    spacing: 6px;
    padding: 2px;
}

QCheckBox::indicator,
QRadioButton::indicator {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {
    background-color: #3f1d33;
    border-color: #3f391d;
}

QPushButton {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
    border-radius: 3px;
    color: #e5d99e;
    min-height: 28px;
    padding: 5px 11px;
}

QPushButton:hover,
QPushButton:checked {
    background-color: #3f1d33;
    border-color: #3f391d;
    color: #e5d99e;
}

QPushButton:pressed {
    background-color: #2c1424;
}

QPushButton:disabled {
    background-color: #14282c;
    border-color: #3f391d;
    color: #3f391d;
}

QPushButton[primary="true"] {
    background-color: #2c1424;
    border-color: #3f391d;
    color: #e5d99e;
    font-weight: bold;
}

QPushButton[primary="true"]:hover {
    background-color: #3f1d33;
}

QTabWidget::pane {
    border: 1px solid #3f391d;
    background-color: #14282c;
}

QTabBar::tab {
    background-color: #14282c;
    border: 1px solid #3f391d;
    border-bottom: none;
    color: #e5d99e;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:hover,
QTabBar::tab:selected {
    background-color: #3f1d33;
    color: #e5d99e;
    border-color: #3f391d;
}

QTableWidget,
QTableView,
QListWidget,
QTreeWidget {
    background-color: #1d3a3f;
    alternate-background-color: #14282c;
    border: 1px solid #3f391d;
    color: #e5d99e;
    gridline-color: #3f391d;
    selection-background-color: #3f1d33;
    selection-color: #e5d99e;
}

QHeaderView::section {
    background-color: #2c1424;
    border: none;
    border-right: 1px solid #3f391d;
    border-bottom: 1px solid #3f391d;
    color: #e5d99e;
    padding: 5px 6px;
    font-weight: bold;
}

QListWidget::item {
    padding: 5px;
}

QListWidget::item:selected {
    background-color: #3f1d33;
    color: #e5d99e;
}

QProgressBar {
    background-color: #1d3a3f;
    border: 1px solid #3f391d;
    border-radius: 3px;
    color: #e5d99e;
    text-align: center;
    min-height: 16px;
}

QProgressBar::chunk {
    background-color: #3f1d33;
    border-radius: 2px;
}

QScrollArea {
    background-color: #14282c;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #14282c;
}

QScrollBar:vertical,
QScrollBar:horizontal {
    background: #14282c;
}

QScrollBar:vertical {
    width: 9px;
}

QScrollBar:horizontal {
    height: 9px;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #1d3a3f;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    min-height: 28px;
}

QScrollBar::handle:horizontal {
    min-width: 28px;
}

QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: #3f1d33;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}

QToolTip {
    background-color: #2c1424;
    border: 1px solid #3f391d;
    color: #e5d99e;
    padding: 4px;
}

QFrame[foundryCard="true"] {
    background-color: #14282c;
    border: 2px solid #3f391d;
    border-radius: 7px;
}

QWidget[cardHeader="true"] {
    background-color: #2c1424;
    border-bottom: 2px solid #3f391d;
}

QLabel[cardIcon="true"] {
    background-color: transparent;
    color: #e5d99e;
}

QFrame[achievementBrowserCard="true"] {
    background-color: transparent;
    border: none;
}

QFrame[achievementBrowserCard="true"] QWidget[cardHeader="true"] {
    min-height: 0px;
    border: none;
}

QFrame[foundryCard="true"] QWidget[cardHeader="true"] {
    min-height: 34px;
    max-height: 34px;
}
"""


def apply_foundry_theme(app: QApplication) -> None:
    """Apply the Black Feather Foundry global theme."""
    app.setStyle("Fusion")
    app.setStyleSheet(FOUNDry_STYLESHEET)
    app.setFont(QFont("Segoe UI", 9))
