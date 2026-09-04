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
    QToolButton,
    QSizePolicy,
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
        # Status text is transient information, not a layout constraint. Long
        # optimizer/audit messages must never force an entire Foundry page wider.
        self.message.setMinimumWidth(0)
        self.message.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
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
        self.center_label.setMinimumWidth(0)
        self.center_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
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
        self.center_label.setToolTip(text)

    def add_action(
        self,
        icon_text: str,
        on_click=None,
        tooltip: str = "",
    ) -> QToolButton:
        """
        Add a small icon button to the far right of the
        status bar (e.g. a refresh or settings glyph).
        Returns the button so the caller can keep a
        reference if needed.
        """

        button = QToolButton()

        button.setText(icon_text)

        button.setProperty(
            "statusAction",
            True,
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        if tooltip:
            button.setToolTip(tooltip)

        if on_click is not None:
            button.clicked.connect(on_click)

        self.actions_layout.addWidget(button)

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

        self._set_message(text)

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

        self._set_message(text)

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

        self._set_message(text)

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

        self._set_message(text)

        self._refresh()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _set_message(self, text: str) -> None:
        value = str(text or "")
        self.message.setText(value)
        self.message.setToolTip(value)

    def _refresh(self):

        self.icon.style().unpolish(
            self.icon
        )

        self.icon.style().polish(
            self.icon
        )
