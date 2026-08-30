# ==================================================
# Black Feather Foundry
#
# File:
# widgets/stream_controls.py
#
# Purpose:
# Live stream operation controls.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class StreamControls(QWidget):
    """Controls for live stream operations."""

    brbRequested = Signal()
    endStreamRequested = Signal()
    resetSessionRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.brb_button = QPushButton("☕  BRB")
        self.end_stream_button = QPushButton("☾  END STREAM")
        self.reset_button = QPushButton("⟳  RESET SESSION")

        for button in (self.brb_button, self.end_stream_button, self.reset_button):
            button.setMinimumHeight(36)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.brb_button)
        layout.addWidget(self.end_stream_button)
        layout.addWidget(self.reset_button)
        layout.addStretch()

        self.brb_button.clicked.connect(self.brbRequested.emit)
        self.end_stream_button.clicked.connect(self.endStreamRequested.emit)
        self.reset_button.clicked.connect(self.resetSessionRequested.emit)
