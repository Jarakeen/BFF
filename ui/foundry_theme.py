from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

FOUNDry_STYLESHEET = r"""
/* ==========================================================
   BLACK FEATHER FOUNDRY
   Soft Chocolate / Bronze Theme
   ========================================================== */

QWidget {
    background-color: #0d0f0e;
    color: #d8d0c2;
    font-family: "Segoe UI";
    font-size: 12px;
}

QMainWindow {
    background-color: #0d0f0e;
}

/* ----------------------------------------------------------
   Sidebar / Branding
   ---------------------------------------------------------- */

#sidebar {
    background-color: #101310;
    border-right: 1px solid #383025;
}

#brandMark {
    color: #c39a5c;
    font-size: 34px;
}

#brandTitle {
    color: #ddd5c7;
    font-family: Georgia, "Times New Roman";
    font-size: 23px;
    font-weight: bold;
    letter-spacing: 1px;
}

#brandSubtitle {
    color: #b9955d;
    font-family: Georgia, "Times New Roman";
    font-size: 11px;
    letter-spacing: 2px;
}

#reminder {
    background-color: #171512;
    border: 1px solid #3b3124;
    border-radius: 4px;
    color: #bdb4a5;
    padding: 9px;
}

#sidebarFooter {
    color: #777268;
    font-size: 9px;
    letter-spacing: 1px;
}

#pageTitle {
    background-color: transparent;
    color: #ded6c8;
    font-family: Georgia, "Times New Roman";
    font-size: 27px;
    font-weight: bold;
    letter-spacing: 0px;
    padding: 2px 0px;
}

#pageSubtitle {
    background-color: transparent;
    color: #b9955d;
    font-family: Georgia, "Times New Roman";
    font-size: 11px;
}

#statusLabel {
    background-color: #101310;
    border-top: 1px solid #383025;
    color: #7f786e;
    padding: 5px 8px;
}

/* ----------------------------------------------------------
   Navigation
   ---------------------------------------------------------- */

QPushButton[nav="true"] {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    color: #bdb5a8;
    min-height: 31px;
    padding: 5px 10px;
    text-align: left;
}

QPushButton[nav="true"]:hover {
    background-color: #211b13;
    border-color: #4a3b27;
    color: #d8d0c2;
}

QPushButton[nav="true"]:checked {
    background-color: #302516;
    border-color: #69502d;
    color: #caa467;
    font-weight: bold;
}

/* ----------------------------------------------------------
   Cards / Groups
   ---------------------------------------------------------- */

QGroupBox {
    background-color: #141714;
    border: 1px solid #3d3427;
    border-radius: 5px;
    margin-top: 11px;
    padding: 11px 9px 8px 9px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0px 7px;
    color: #c5a06a;
    background-color: #141714;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
    font-weight: bold;
}

/* ----------------------------------------------------------
   Labels
   ---------------------------------------------------------- */

QLabel {
    background-color: transparent;
    color: #d2cabd;
}

QLabel[section="true"] {
    color: #c5a06a;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: bold;
}

/* ----------------------------------------------------------
   Inputs
   ---------------------------------------------------------- */

QLineEdit,
QTextEdit,
QPlainTextEdit {
    background-color: #151815;
    border: 1px solid #39342c;
    border-radius: 3px;
    color: #d8d0c2;
    padding: 5px 7px;
    selection-background-color: #66502f;
    selection-color: #eee7dc;
}

QLineEdit:hover,
QTextEdit:hover,
QPlainTextEdit:hover {
    border-color: #55452f;
}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {
    border: 1px solid #987645;
    background-color: #171a17;
}

QLineEdit:disabled,
QTextEdit:disabled,
QPlainTextEdit:disabled {
    background-color: #101210;
    color: #59554e;
}

/* ----------------------------------------------------------
   Combo Boxes
   ---------------------------------------------------------- */

QComboBox {
    background-color: #151815;
    border: 1px solid #39342c;
    border-radius: 3px;
    color: #d8d0c2;
    min-height: 26px;
    padding: 2px 7px;
}

QComboBox:hover,
QComboBox:focus {
    border-color: #987645;
}

QComboBox::drop-down {
    width: 24px;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #171a17;
    border: 1px solid #4a3b27;
    color: #d8d0c2;
    selection-background-color: #342918;
    selection-color: #eee7dc;
    padding: 3px;
}

/* ----------------------------------------------------------
   Checkboxes / Radio Buttons
   ---------------------------------------------------------- */

QCheckBox,
QRadioButton {
    background-color: transparent;
    color: #bdb5a8;
    spacing: 6px;
    padding: 2px;
}

QCheckBox:hover,
QRadioButton:hover {
    color: #d8d0c2;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    background-color: #151815;
    border: 1px solid #5b4d38;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #9a7745;
    border-color: #c5a06a;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    background-color: #151815;
    border: 1px solid #5b4d38;
    border-radius: 7px;
}

QRadioButton::indicator:checked {
    background-color: #9a7745;
    border-color: #c5a06a;
}

/* ----------------------------------------------------------
   Buttons
   ---------------------------------------------------------- */

QPushButton {
    background-color: #211a12;
    border: 1px solid #59472d;
    border-radius: 3px;
    color: #cec5b6;
    min-height: 28px;
    padding: 5px 11px;
}

QPushButton:hover {
    background-color: #302418;
    border-color: #987645;
    color: #e1d8c9;
}

QPushButton:pressed {
    background-color: #18130e;
    border-color: #765a34;
}

QPushButton:disabled {
    background-color: #151715;
    border-color: #2d2d28;
    color: #5b5852;
}

QPushButton[primary="true"] {
    background-color: #4b381d;
    border-color: #987645;
    color: #e6d8bf;
    font-weight: bold;
}

QPushButton[primary="true"]:hover {
    background-color: #5a4322;
}

/* ----------------------------------------------------------
   Tabs
   ---------------------------------------------------------- */

QTabWidget::pane {
    border: 1px solid #3d3427;
    background-color: #141714;
}

QTabBar::tab {
    background-color: #121512;
    border: 1px solid #39342c;
    border-bottom: none;
    color: #817b71;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:hover {
    color: #c9c0b2;
}

QTabBar::tab:selected {
    background-color: #2a2116;
    color: #c5a06a;
    border-color: #69502d;
}

/* ----------------------------------------------------------
   Tables / Lists
   ---------------------------------------------------------- */

QTableWidget,
QTableView,
QListWidget,
QTreeWidget {
    background-color: #111411;
    alternate-background-color: #151815;
    border: 1px solid #3d3427;
    color: #d0c8bb;
    gridline-color: #272923;
    selection-background-color: #342918;
    selection-color: #e1d9cb;
}

QHeaderView::section {
    background-color: #211a12;
    border: none;
    border-right: 1px solid #3d3427;
    border-bottom: 1px solid #3d3427;
    color: #b9955d;
    padding: 5px 6px;
    font-weight: bold;
}

QListWidget::item {
    padding: 5px;
}

QListWidget::item:selected {
    background-color: #342918;
    color: #ddd5c8;
}

/* ----------------------------------------------------------
   Scrollbars
   ---------------------------------------------------------- */

QScrollBar:vertical {
    background: #0d0f0e;
    width: 9px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #4a3b28;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #725731;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0d0f0e;
    height: 9px;
}

QScrollBar::handle:horizontal {
    background: #4a3b28;
    min-width: 28px;
    border-radius: 4px;
}

/* ----------------------------------------------------------
   Progress
   ---------------------------------------------------------- */

QProgressBar {
    background-color: #111411;
    border: 1px solid #3d3427;
    border-radius: 3px;
    color: #cfc6b8;
    text-align: center;
    min-height: 16px;
}

QProgressBar::chunk {
    background-color: #8f7043;
    border-radius: 2px;
}

/* ----------------------------------------------------------
   Scroll Areas
   ---------------------------------------------------------- */

QScrollArea {
    background-color: #0d0f0e;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #0d0f0e;
}

QScrollBar:vertical {
    background: #0d0f0e;
    width: 2px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #4a3b28;
    min-height: 28px;
    border-radius: 2px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0d0f0e;
    height: 2px;
}

QScrollBar::handle:horizontal {
    background: #4a3b28;
    min-width: 28px;
    border-radius: 2px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ----------------------------------------------------------
   Tooltips
   ---------------------------------------------------------- */

QToolTip {
    background-color: #211a12;
    border: 1px solid #59472d;
    color: #d8d0c2;
    padding: 4px;
}
"""


def apply_foundry_theme(app: QApplication) -> None:
    """Apply the Black Feather Foundry global theme."""
    app.setStyle("Fusion")
    app.setStyleSheet(FOUNDry_STYLESHEET)
    app.setFont(QFont("Segoe UI", 9))


    