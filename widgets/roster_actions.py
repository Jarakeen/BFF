# ==================================================
# Black Feather Foundry
#
# File:
# widgets/roster_actions.py
#
# Purpose:
# Standard action bar for the Roster page.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class RosterActions(QWidget):
    """
    Action buttons for the Roster page.
    """

    newRequested = Signal()
    saveRequested = Signal()
    deleteRequested = Signal()
    refreshRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.new_button = QPushButton(
            "New Player"
        )

        self.save_button = QPushButton(
            "Save"
        )

        self.delete_button = QPushButton(
            "Delete"
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.new_button)

        layout.addWidget(self.save_button)

        layout.addWidget(self.delete_button)

        layout.addWidget(self.refresh_button)

        #
        # Signals
        #

        self.new_button.clicked.connect(
            self.newRequested.emit
        )

        self.save_button.clicked.connect(
            self.saveRequested.emit
        )

        self.delete_button.clicked.connect(
            self.deleteRequested.emit
        )

        self.refresh_button.clicked.connect(
            self.refreshRequested.emit
        )
