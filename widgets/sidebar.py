# ==================================================
# Black Feather Foundry
#
# File:
# widgets/sidebar.py
#
# Purpose:
# Primary application navigation.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
)


class Sidebar(QWidget):
    """
    Primary Foundry navigation.
    """

    pageRequested = Signal(str)

    PAGES = [

        ("Broadcast Desk",      "broadcast"),

        ("Field Office",        "field_office"),

        ("Live Operations",    "live_operations"),

        ("Archive",             "archive"),

        ("Incident Desk",      "incident"),

        ("Achievement Desk",   "achievement"),

        ("Collections",        "collections"),

        ("Operations Console", "console"),

        ("Settings",            "settings"),

    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(260)

        self.build_ui()

        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        title = QLabel(
            "\nBlack Feather\nFoundry"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setObjectName(
            "SidebarTitle"
        )

        divider1 = QFrame()

        divider1.setFrameShape(
            QFrame.Shape.HLine
        )

        self.navigation = QListWidget()

        self.navigation.setSpacing(4)

        for text, page in self.PAGES:

            item = QListWidgetItem(text)

            item.setData(
                Qt.ItemDataRole.UserRole,
                page,
            )

            self.navigation.addItem(item)

        divider2 = QFrame()

        divider2.setFrameShape(
            QFrame.Shape.HLine
        )

        reminder = QLabel(

            "Remember:\n\n"

            "• Check the quest log\n"

            "• Read the achievements\n"

            "• Communicate\n"

            "• Drink coffee"

        )

        reminder.setWordWrap(True)

        reminder.setObjectName(
            "SidebarReminder"
        )

        divider3 = QFrame()

        divider3.setFrameShape(
            QFrame.Shape.HLine
        )

        self.status = QLabel(
            "● Ready"
        )

        self.status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(10)

        layout.addWidget(title)

        layout.addWidget(divider1)

        layout.addWidget(
            self.navigation,
            1,
        )

        layout.addWidget(divider2)

        layout.addWidget(reminder)

        layout.addWidget(divider3)

        layout.addWidget(self.status)

        self.navigation.setCurrentRow(0)

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.navigation.currentItemChanged.connect(
            self.page_changed
        )

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def page_changed(self, current, previous):

        if current is None:
            return

        page = current.data(
            Qt.ItemDataRole.UserRole
        )

        self.pageRequested.emit(page)

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def set_status(self, text: str):

        self.status.setText(text)