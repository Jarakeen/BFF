# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_status_bar.py
#
# Purpose:
# Standard status display used throughout the
# Foundry.
#
# ==================================================

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

        self.icon = QLabel("●")
        self.icon.setProperty(
            "statusIcon",
            True,
        )

        self.message = QLabel("Ready")
        self.message.setFont(
            Fonts.status()
        )

        self.message.setProperty(
            "statusMessage",
            True,
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            12,
            6,
            12,
            6,
        )

        layout.setSpacing(8)

        layout.addWidget(self.icon)

        layout.addWidget(
            self.message,
            1,
        )

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def info(self, message: str):

        self.icon.setText("ℹ")

        self.message.setText(message)

    def success(self, message: str):

        self.icon.setText("✓")

        self.message.setText(message)

    def warning(self, message: str):

        self.icon.setText("⚠")

        self.message.setText(message)

    def error(self, message: str):

        self.icon.setText("✖")

        self.message.setText(message)

    def clear(self):

        self.icon.setText("●")

        self.message.setText("Ready")