# ==================================================
# Black Feather Foundry
#
# File:
# widgets/achievement_actions.py
#
# Purpose:
# Action buttons for the Achievement Desk.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class AchievementActions(QWidget):
    """
    Action buttons for the Achievement Desk.
    """

    prepareRequested = Signal()

    sendRequested = Signal()

    archiveRequested = Signal()

    clearRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.prepare_button = QPushButton(
            "Prepare Run"
        )

        self.send_button = QPushButton(
            "Send to OBS"
        )

        self.archive_button = QPushButton(
            "Archive Run"
        )

        self.clear_button = QPushButton(
            "Clear"
        )

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.prepare_button)

        layout.addWidget(self.send_button)

        layout.addWidget(self.archive_button)

        layout.addStretch()

        layout.addWidget(self.clear_button)

        #
        # Signals
        #

        self.prepare_button.clicked.connect(
            self.prepareRequested.emit
        )

        self.send_button.clicked.connect(
            self.sendRequested.emit
        )

        self.archive_button.clicked.connect(
            self.archiveRequested.emit
        )

        self.clear_button.clicked.connect(
            self.clearRequested.emit
        )