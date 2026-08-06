# ==================================================
# Black Feather Foundry
#
# File:
# widgets/alert_controls.py
#
# Purpose:
# Test controls for StreamElements alerts.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
)


class AlertControls(QWidget):
    """
    Controls for testing StreamElements alerts.
    """

    followRequested = Signal()
    subscriptionRequested = Signal()
    raidRequested = Signal()
    cheerRequested = Signal()
    allRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.follow_button = QPushButton("Follow")

        self.subscription_button = QPushButton("Subscription")

        self.raid_button = QPushButton("Raid")

        self.cheer_button = QPushButton("Cheer")

        self.all_button = QPushButton("Test All")

        #
        # Layout
        #

        layout = QGridLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.follow_button,
            0,
            0,
        )

        layout.addWidget(
            self.subscription_button,
            0,
            1,
        )

        layout.addWidget(
            self.raid_button,
            1,
            0,
        )

        layout.addWidget(
            self.cheer_button,
            1,
            1,
        )

        layout.addWidget(
            self.all_button,
            2,
            0,
            1,
            2,
        )

        #
        # Signals
        #

        self.follow_button.clicked.connect(
            self.followRequested.emit
        )

        self.subscription_button.clicked.connect(
            self.subscriptionRequested.emit
        )

        self.raid_button.clicked.connect(
            self.raidRequested.emit
        )

        self.cheer_button.clicked.connect(
            self.cheerRequested.emit
        )

        self.all_button.clicked.connect(
            self.allRequested.emit
        )