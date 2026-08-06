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

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
)


class BroadcastActions(QWidget):
    """
    Standard action buttons used by the Broadcast Desk.
    """

    clearRequested = Signal()
    generateRequested = Signal()
    saveToOBSRequested = Signal()
    archiveRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.generate_button = QPushButton(
            "Generate Broadcast"
        )

        self.clear_button = QPushButton(
            "Clear"
        )

        self.obs_button = QPushButton(
            "Save to OBS"
        )

        self.archive_button = QPushButton(
            "Save to Archive"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.generate_button)
        layout.addStretch()
        layout.addWidget(self.clear_button)
        layout.addWidget(self.obs_button)
        layout.addWidget(self.archive_button)

        #
        # Signals
        #

        self.generate_button.clicked.connect(
            self.generateRequested.emit
        )

        self.clear_button.clicked.connect(
            self.clearRequested.emit
        )

        self.obs_button.clicked.connect(
            self.saveToOBSRequested.emit
        )

        self.archive_button.clicked.connect(
            self.archiveRequested.emit
        )