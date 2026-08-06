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

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class StreamControls(QWidget):
    """
    Controls for live stream operations.
    """

    brbRequested = Signal()
    endStreamRequested = Signal()
    resetSessionRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.brb_button = QPushButton(
            "☕ BRB"
        )

        self.end_stream_button = QPushButton(
            "🌙 End Stream"
        )

        self.reset_button = QPushButton(
            "Reset Session"
        )

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.brb_button
        )

        layout.addWidget(
            self.end_stream_button
        )

        layout.addStretch()

        layout.addWidget(
            self.reset_button
        )

        #
        # Signals
        #

        self.brb_button.clicked.connect(
            self.brbRequested.emit
        )

        self.end_stream_button.clicked.connect(
            self.endStreamRequested.emit
        )

        self.reset_button.clicked.connect(
            self.resetSessionRequested.emit
        )