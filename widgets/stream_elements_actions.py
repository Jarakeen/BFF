# ==================================================
# Black Feather Foundry
#
# File:
# widgets/stream_elements_actions.py
#
# Purpose:
# Action buttons for Stream Elements.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
)


class StreamElementsActions(QWidget):
    """
    Standard action buttons for Stream Elements.
    """

    reconnectRequested = Signal()
    refreshRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Buttons
        #

        self.reconnect_button = QPushButton(
            "Reconnect OBS"
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )

        self.settings_button = QPushButton(
            "Settings"
        )

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.reconnect_button
        )

        layout.addWidget(
            self.refresh_button
        )

        layout.addStretch()

        layout.addWidget(
            self.settings_button
        )

        #
        # Signals
        #

        self.reconnect_button.clicked.connect(
            self.reconnectRequested.emit
        )

        self.refresh_button.clicked.connect(
            self.refreshRequested.emit
        )

        self.settings_button.clicked.connect(
            self.settingsRequested.emit
        )