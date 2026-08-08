# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_status_bar.py
#
# Purpose:
# Standard status bar used throughout the
# Foundry.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
)

from ui.theme.fonts import Fonts


class FoundryStatusBar(QWidget):
    """
    Standard Foundry status bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setProperty(
            "foundryStatusBar",
            True,
        )

        #
        # Icon
        #

        self.icon = QLabel("●")

        self.icon.setProperty(
            "statusIcon",
            True,
        )

        #
        # Message
        #

        self.message = QLabel(
            "Ready."
        )

        self.message.setFont(
            Fonts.status()
        )

        self.message.setProperty(
            "statusMessage",
            True,
        )

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )

        layout.setSpacing(8)

        layout.addWidget(self.icon)

        layout.addWidget(
            self.message,
            1,
        )

        #
        # Initial state
        #

        self.info("Ready.")

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def info(
        self,
        text: str,
    ):

        self.icon.setText("●")

        self.icon.setProperty(
            "statusRole",
            "info",
        )

        self.message.setText(text)

        self._refresh()

    def success(
        self,
        text: str,
    ):

        self.icon.setText("●")

        self.icon.setProperty(
            "statusRole",
            "success",
        )

        self.message.setText(text)

        self._refresh()

    def warning(
        self,
        text: str,
    ):

        self.icon.setText("●")

        self.icon.setProperty(
            "statusRole",
            "warning",
        )

        self.message.setText(text)

        self._refresh()

    def error(
        self,
        text: str,
    ):

        self.icon.setText("●")

        self.icon.setProperty(
            "statusRole",
            "error",
        )

        self.message.setText(text)

        self._refresh()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _refresh(self):

        self.icon.style().unpolish(
            self.icon
        )

        self.icon.style().polish(
            self.icon
        )