# ==================================================
# Black Feather Foundry
#
# File:
# widgets/status_panel.py
#
# Purpose:
# Standard status display for the Foundry.
#
# ==================================================

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
)


class StatusPanel(QWidget):
    """
    Standard Foundry status panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon = QLabel("●")
        self.message = QLabel("Ready")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.icon)
        layout.addWidget(self.message)
        layout.addStretch()

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