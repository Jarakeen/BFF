# ==================================================
# Black Feather Foundry
#
# File:
# widgets/collection_actions.py
#
# Purpose:
# Action buttons for the Collections page.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class CollectionActions(QWidget):
    """
    Action buttons for the Collections page.
    """

    refreshRequested = Signal()
    syncRequested = Signal()
    exportRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.refresh_button = QPushButton("Refresh")

        self.sync_button = QPushButton("Synchronize")

        self.export_button = QPushButton("Export")

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.refresh_button)

        layout.addWidget(self.sync_button)

        layout.addWidget(self.export_button)

        layout.addStretch()

        self.refresh_button.clicked.connect(
            self.refreshRequested.emit
        )

        self.sync_button.clicked.connect(
            self.syncRequested.emit
        )

        self.export_button.clicked.connect(
            self.exportRequested.emit
        )