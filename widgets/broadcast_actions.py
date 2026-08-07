# ==================================================
# Black Feather Foundry
#
# File:
# widgets/broadcast_actions.py
#
# Purpose:
# Standard action bar for the Broadcast Desk.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class BroadcastActions(QWidget):
    """
    Action buttons for the Broadcast Desk.
    """

    generateRequested = Signal()
    saveRequested = Signal()
    archiveRequested = Signal()
    clearRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.generate_button = QPushButton(
            "Generate"
        )

        self.save_button = QPushButton(
            "Send to OBS"
        )

        self.archive_button = QPushButton(
            "Archive"
        )

        self.clear_button = QPushButton(
            "Clear"
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.generate_button)

        # layout.addStretch()

        layout.addWidget(self.save_button)

        layout.addWidget(self.archive_button)

        layout.addWidget(self.clear_button)

        #
        # Signals
        #

        self.generate_button.clicked.connect(
            self.generateRequested.emit
        )

        self.save_button.clicked.connect(
            self.saveRequested.emit
        )

        self.archive_button.clicked.connect(
            self.archiveRequested.emit
        )

        self.clear_button.clicked.connect(
            self.clearRequested.emit
        )