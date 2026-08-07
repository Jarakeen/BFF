# ==================================================
# Black Feather Foundry
#
# File:
# widgets/field_notes_actions.py
#
# Purpose:
# Action buttons for the Field Notes page.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class FieldNotesActions(QWidget):
    """
    Standard action buttons for Field Notes.
    """

    saveRequested = Signal()
    clearRequested = Signal()
    archiveRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.save_button = QPushButton("Save")

        self.clear_button = QPushButton("Clear")

        self.archive_button = QPushButton("Archive")

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.save_button)

        layout.addWidget(self.clear_button)

        # layout.addStretch()

        layout.addWidget(self.archive_button)

        #
        # Signals
        #

        self.save_button.clicked.connect(
            self.saveRequested.emit
        )

        self.clear_button.clicked.connect(
            self.clearRequested.emit
        )

        self.archive_button.clicked.connect(
            self.archiveRequested.emit
        )