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

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QToolButton,
)

from ui.theme.fonts import Fonts


class FoundryStatusBar(QWidget):
    """
    Standard Foundry status bar.

    [ ● message ]                [ center ]              [ actions ● ]
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
        # Center (optional)
        #
        # e.g. "THE CONSOLE v0.1.0". Empty by default.
        #

        self.center_label = QLabel("")

        self.center_label.setFont(
            Fonts.status()
        )

        self.center_label.setAlignment(
            Qt.AlignCenter
        )

        self.center_label.setProperty(
            "statusCenter",
            True,
        )

        #
        # Trailing actions (optional)
        #
        # Icon buttons docked to the far right (refresh,
        # settings, ...), in addition to the built-in
        # connection dot.
        #

        self.actions_layout = QHBoxLayout()

        self.actions_layout.setContentsMargins(
            0, 0, 0, 0,
        )

        self.actions_layout.setSpacing(6)

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

        layout.addWidget(
            self.center_label,
            1,
        )

        layout.addLayout(
            self.actions_layout
        )

        #
        # Initial state
        #

        self.info("Ready.")

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_center_text(
        self,
        text: str,
    ):

        self.center_label.setText(text)

    def add_action(
        self,
        icon_text: str,
        on_click=None,
        tooltip: str = "",
    ) -> QToolButton:
        """
        Add a session action to the right side of the status bar.
        """

        button = QToolButton()

        button.setProperty(
            "statusAction",
            True,
        )
      

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setMinimumSize(
            48,
            44,
        )
        button.setIconSize(
            QSize(
                40,
                40,
            )
        )

        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )

        if tooltip:
            button.setToolTip(
                tooltip
            )

        if on_click is not None:
            button.clicked.connect(
                on_click
            )

        self.actions_layout.addWidget(
            button
        )

        return button

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