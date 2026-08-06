# ==================================================
# Black Feather Foundry
#
# File:
# ui/operations_console.py
#
# Purpose:
# Operations Console.
#
# Central command interface for the
# Black Feather Foundry.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
)

from widgets.page_header import PageHeader
from widgets.status_panel import StatusPanel

from ui.components.section_card import SectionCard


class OperationsConsole(QWidget):
    """
    Central command interface.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = PageHeader(
            title="Operations Console",
            subtitle="Mission control for expeditions, raids, and research.",
            department="Command",
        )

        #
        # Navigation
        #

        self.navigation = QListWidget()

        pages = [
            "Dashboard",
            "Raid",
            "Builds",
            "Capabilities",
            "Boss Guide",
            "Assignments",
            "Optimization",
            "Progression",
            "Reference",
            "Settings",
        ]

        for page in pages:

            self.navigation.addItem(
                QListWidgetItem(page)
            )

        #
        # Content
        #

        self.stack = QStackedWidget()

        for page in pages:

            widget = QWidget()

            layout = QVBoxLayout(widget)

            title = QLabel(page)

            title.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            layout.addStretch()

            layout.addWidget(title)

            layout.addStretch()

            self.stack.addWidget(widget)

        #
        # Status
        #

        self.status = StatusPanel()

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(12)

        layout.addWidget(
            self.header
        )

        body = QHBoxLayout()

        #
        # Left navigation
        #

        navigation = SectionCard(
            "Navigation"
        )

        navigation.addWidget(
            self.navigation
        )

        #
        # Right content
        #

        content = SectionCard(
            "Console"
        )

        content.addWidget(
            self.stack
        )

        body.addWidget(
            navigation,
            1,
        )

        body.addWidget(
            content,
            4,
        )

        layout.addLayout(
            body
        )

        layout.addWidget(
            self.status
        )

        self.navigation.setCurrentRow(0)

        self.status.info(
            "Operations Console ready."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.navigation.currentRowChanged.connect(
            self.stack.setCurrentIndex
        )