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
    QVBoxLayout,
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
            subtitle=(
                "Mission control for expeditions, raids, "
                "and research."
            ),
            department="Command",
        )

        # --------------------------------------------------
        # Main content
        # --------------------------------------------------

        self.content_widget = QWidget()

        content_layout = QVBoxLayout(
            self.content_widget
        )

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        title = QLabel(
            "Operations Console"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        content_layout.addWidget(
            title
        )

        content_layout.addStretch()

        # --------------------------------------------------
        # Console card
        # --------------------------------------------------

        content = FoundryCard(
            "Console"
        )

        content.addWidget(
            self.content_widget
        )

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        self.status = FoundryStatusBar()

        # --------------------------------------------------
        # Main layout
        # --------------------------------------------------

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

        layout.addWidget(
            content,
            1,
        )

        layout.addWidget(
            self.status
        )

        self.status.info(
            "Operations Console ready."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):
        """
        Operations Console currently has no local
        navigation signals.

        Navigation is handled by the main FoundryDock
        sidebar.
        """
        pass