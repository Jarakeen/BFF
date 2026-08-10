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

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from services.expedition_service import ExpeditionService
from services.raid_service import RaidService
from services.statistics_engine import StatisticsEngine
from ui.components.foundry_card import FoundryCard


class OperationsConsole(QWidget):
    """
    Central command interface.
    """

    def __init__(
        self,
        expedition: ExpeditionService,
        parent=None,
    ):
        super().__init__(parent)

        self.expedition = expedition

        self.raid = RaidService(
            expedition=self.expedition
        )

        self.statistics = StatisticsEngine()

        self.build_ui()

        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = FoundryHeader(
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

            # layout.addStretch()

            layout.addWidget(title)

            # layout.addStretch()

            self.stack.addWidget(widget)

        #
        # Status
        #

        self.status = FoundryStatusBar()

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

        layout.setSpacing(8)

        layout.addWidget(
            self.header
        )

        body = QHBoxLayout()

        #
        # Left navigation
        #

        navigation = FoundryCard(
            "Navigation"
        )

        navigation.addWidget(
            self.navigation
        )

        #
        # Right content
        #

        content = FoundryCard(
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