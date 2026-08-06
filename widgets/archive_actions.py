# ==================================================
# Black Feather Foundry
#
# File:
# widgets/archive_actions.py
#
# Purpose:
# Action buttons for the Archive page.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class ArchiveActions(QWidget):
    """
    Action buttons for Archive operations.
    """

    openRequested = Signal()
    revealRequested = Signal()
    exportRequested = Signal()
    refreshRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.open_button = QPushButton(
            "Open"
        )

        self.reveal_button = QPushButton(
            "Open Folder"
        )

        self.export_button = QPushButton(
            "Export"
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.open_button)
        layout.addWidget(self.reveal_button)
        layout.addWidget(self.export_button)

        layout.addStretch()

        layout.addWidget(self.refresh_button)

        #
        # Signals
        #

        self.open_button.clicked.connect(
            self.openRequested.emit
        )

        self.reveal_button.clicked.connect(
            self.revealRequested.emit
        )

        self.export_button.clicked.connect(
            self.exportRequested.emit
        )

        self.refresh_button.clicked.connect(
            self.refreshRequested.emit
        )