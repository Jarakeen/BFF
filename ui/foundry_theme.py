from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QDialog


SAFE_DIALOG_BACKGROUND = "#0C171B"


class _DarkDialogPrepaintFilter(QObject):
    """Force top-level dialogs dark before their first visible paint."""

    def eventFilter(self, watched, event):
        if isinstance(watched, QDialog) and event.type() in {
            QEvent.Type.Polish,
            QEvent.Type.Show,
        }:
            watched.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            watched.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            watched.setAutoFillBackground(True)

            palette = watched.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(SAFE_DIALOG_BACKGROUND))
            palette.setColor(QPalette.ColorRole.Base, QColor(SAFE_DIALOG_BACKGROUND))
            watched.setPalette(palette)

            # Apply a direct top-level rule so the native dialog surface has an
            # explicit dark fill even before inherited application QSS settles.
            watched.setStyleSheet(
                f"QDialog {{ background-color: {SAFE_DIALOG_BACKGROUND}; }}"
            )

            # Scroll-area viewports are separate paint surfaces and can briefly
            # expose a platform-default background while a large editor is laid
            # out. Give them the same opaque dark teal prepaint.
            for area in watched.findChildren(QAbstractScrollArea):
                viewport = area.viewport()
                viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                viewport.setAutoFillBackground(True)
                viewport_palette = viewport.palette()
                viewport_palette.setColor(
                    QPalette.ColorRole.Window,
                    QColor(SAFE_DIALOG_BACKGROUND),
                )
                viewport_palette.setColor(
                    QPalette.ColorRole.Base,
                    QColor(SAFE_DIALOG_BACKGROUND),
                )
                viewport.setPalette(viewport_palette)

        return super().eventFilter(watched, event)


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

QMainWindow { background-color: #0d0f0e; }
#sidebar { background-color: #101310; border-right: 1px solid #383025; }
#brandMark { color: #c39a5c; font-size: 34px; }
#brandTitle { color: #ddd5c7; font-family: Georgia, "Times New Roman"; font-size: 23px; font-weight: bold; letter-spacing: 1px; }
#brandSubtitle { color: #b9955d; font-family: Georgia, "Times New Roman"; font-size: 11px; letter-spacing: 2px; }
#reminder { background-color: #171512; border: 1px solid #3b3124; border-radius: 4px; color: #bdb4a5; padding: 9px; }
#sidebarFooter { color: #777268; font-size: 9px; letter-spacing: 1px; }
#pageTitle { background-color: transparent; color: #ded6c8; font-family: Georgia, "Times New Roman"; font-size: 27px; font-weight: bold; letter-spacing: 0px; padding: 2px 0px; }
#pageSubtitle { background-color: transparent; color: #b9955d; font-family: Georgia, "Times New Roman"; font-size: 11px; }
#statusLabel { background-color: #101310; border-top: 1px solid #383025; color: #7f786e; padding: 5px 8px; }

QPushButton[nav="true"] { background-color: transparent; border: 1px solid transparent; border-radius: 3px; color: #bdb5a8; min-height: 31px; padding: 5px 10px; text-align: left; }
QPushButton[nav="true"]:hover { background-color: #211b13; border-color: #4a3b27; color: #d8d0c2; }
QPushButton[nav="true"]:checked { background-color: #302516; border-color: #69502d; color: #caa467; font-weight: bold; }

QGroupBox { background-color: #141714; border: 1px solid #3d3427; border-radius: 5px; margin-top: 11px; padding: 11px 9px 8px 9px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0px 7px; color: #c5a06a; background-color: #141714; font-family: Georgia, "Times New Roman"; font-size: 13px; font-weight: bold; }

QLabel { background-color: transparent; color: #d2cabd; }
QLabel[section="true"] { color: #c5a06a; font-family: Georgia, "Times New Roman"; font-size: 14px; font-weight: bold; }

QLineEdit, QTextEdit, QPlainTextEdit { background-color: #151815; border: 1px solid #39342c; border-radius: 3px; color: #d8d0c2; padding: 5px 7px; selection-background-color: #66502f; selection-color: #eee7dc; }
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover { border-color: #55452f; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #987645; background-color: #171a17; }
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled { background-color: #101210; color: #59554e; }

QComboBox { background-color: #151815; border: 1px solid #39342c; border-radius: 3px; color: #d8d0c2; min-height: 26px; padding: 2px 7px; }
QComboBox:hover, QComboBox:focus { border-color: #987645; }
QComboBox::drop-down { width: 24px; border: none; }
QComboBox QAbstractItemView { background-color: #171a17; border: 1px solid #4a3b27; color: #d8d0c2; selection-background-color: #342918; selection-color: #eee7dc; padding: 3px; }

QCheckBox, QRadioButton { background-color: transparent; color: #bdb5a8; spacing: 6px; padding: 2px; }
QCheckBox:hover, QRadioButton:hover { color: #d8d0c2; }
QCheckBox::indicator { width: 14px; height: 14px; background-color: #151815; border: 1px solid #5b4d38; border-radius: 3px; }
QCheckBox::indicator:checked { background-color: #9a7745; border-color: #c5a06a; }
QRadioButton::indicator { width: 14px; height: 14px; background-color: #151815; border: 1px solid #5b4d38; border-radius: 7px; }
QRadioButton::indicator:checked { background-color: #9a7745; border-color: #c5a06a; }

QPushButton { background-color: #211a12; border: 1px solid #59472d; border-radius: 3px; color: #cec5b6; min-height: 28px; padding: 5px 11px; }
QPushButton:hover { background-color: #302418; border-color: #987645; color: #e1d8c9; }
QPushButton:pressed { background-color: #18130e; border-color: #765a34; }
QPushButton:disabled { background-color: #151715; border-color: #2d2d28; color: #5b5852; }
QPushButton[primary="true"] { background-color: #4b381d; border-color: #987645; color: #e6d8bf; font-weight: bold; }
QPushButton[primary="true"]:hover { background-color: #5a4322; }

QTabWidget::pane { border: 1px solid #3d3427; background-color: #141714; }
QTabBar::tab { background-color: #121512; border: 1px solid #39342c; border-bottom: none; color: #817b71; padding: 6px 12px; margin-right: 2px; }
QTabBar::tab:hover { color: #c9c0b2; }
QTabBar::tab:selected { background-color: #2a2116; color: #c5a06a; border-color: #69502d; }

QTableWidget, QTableView, QListWidget, QTreeWidget { background-color: #111411; alternate-background-color: #151815; border: 1px solid #3d3427; color: #d0c8bb; gridline-color: #272923; selection-background-color: #342918; selection-color: #e1d9cb; }
QHeaderView::section { background-color: #211a12; border: none; border-right: 1px solid #3d3427; border-bottom: 1px solid #3d3427; color: #b9955d; padding: 5px 6px; font-weight: bold; }
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background-color: #342918; color: #ddd5c8; }

QScrollBar:vertical { background: #0d0f0e; width: 9px; margin: 0px; }
QScrollBar::handle:vertical { background: #4a3b28; min-height: 28px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #725731; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: #0d0f0e; height: 9px; }
QScrollBar::handle:horizontal { background: #4a3b28; min-width: 28px; border-radius: 4px; }

QProgressBar { background-color: #111411; border: 1px solid #3d3427; border-radius: 3px; color: #cfc6b8; text-align: center; min-height: 16px; }
QProgressBar::chunk { background-color: #8f7043; border-radius: 2px; }

QScrollArea { background-color: #0d0f0e; border: none; }
QScrollArea > QWidget > QWidget { background-color: #0d0f0e; }
QScrollBar:vertical { background: #0d0f0e; width: 2px; margin: 0px; }
QScrollBar::handle:vertical { background: #4a3b28; min-height: 28px; border-radius: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: #0d0f0e; height: 2px; }
QScrollBar::handle:horizontal { background: #4a3b28; min-width: 28px; border-radius: 2px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QToolTip { background-color: #211a12; border: 1px solid #59472d; color: #d8d0c2; padding: 4px; }

QFrame[foundryCard="true"] { background-color: #141714; border: 2px solid #4a3b27; border-radius: 7px; }
QWidget[cardHeader="true"] { background-color: #1c1915; border-bottom: 2px solid #4a3b27; }
QLabel[cardTitle="true"] { background-color: transparent; color: #d0aa70; font-family: Georgia, "Times New Roman"; font-size: 14px; font-weight: bold; }
QLabel[cardIcon="true"] { background-color: transparent; color: #c39a5c; }
QFrame[achievementBrowserCard="true"] { background-color: transparent; border: none; }
QFrame[achievementBrowserCard="true"] QWidget[cardHeader="true"] { min-height: 0px; border: none; }
QFrame[foundryCard="true"] QWidget[cardHeader="true"] { min-height: 34px; max-height: 34px; }
"""


def apply_foundry_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    # Top-level widgets can be exposed by the window manager before Qt's
    # stylesheet has completed its first paint. Give the application palette
    # the same dark Foundry base colors so dialogs never flash the platform's
    # default white background while their styled children are being polished.
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(SAFE_DIALOG_BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#d8d0c2"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111411"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#151815"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#d8d0c2"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#211a12"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cec5b6"))
    app.setPalette(palette)

    # Keep the filter alive on the QApplication and install it before any
    # later-created modal dialog is polished or shown.
    if not hasattr(app, "_foundry_dark_dialog_filter"):
        app._foundry_dark_dialog_filter = _DarkDialogPrepaintFilter(app)
        app.installEventFilter(app._foundry_dark_dialog_filter)

    app.setStyleSheet(FOUNDry_STYLESHEET)
    app.setFont(QFont("Segoe UI", 9))
