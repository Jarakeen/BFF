# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_empty_state.py
#
# Purpose:
# Generic "nothing here yet" panel for any list, table,
# or graph-driven component above. Icon + message, with
# an optional action button.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_icon import FoundryIcon
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class FoundryEmptyState(QWidget):
    """
    A centered "nothing here yet" panel.

        FoundryEmptyState("No collectibles imported yet.")
        FoundryEmptyState(
            "No roster loaded.",
            icon="roster",
            action_text="Import Roster",
            on_action=do_import,
        )
    """

    def __init__(
        self,
        message: str,
        icon: str | None = None,
        action_text: str | None = None,
        on_action=None,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryEmptyState",
            True,
        )

        layout = QVBoxLayout(self)

        layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.setSpacing(10)

        if icon:

            icon_label = FoundryIcon(
                icon,
                size=Metrics.ICON_LARGE,
                color=Colors.BORDER_HOVER,
            )

            layout.addWidget(
                icon_label,
                0,
                Qt.AlignmentFlag.AlignCenter,
            )

        self.message_label = QLabel(message)

        self.message_label.setProperty(
            "emptyStateMessage",
            True,
        )

        self.message_label.setFont(
            Fonts.subtitle()
        )

        self.message_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.message_label.setWordWrap(True)

        layout.addWidget(self.message_label)

        if action_text:

            self.action_button = FoundryButton(
                action_text,
                role=ButtonRole.SECONDARY,
            )

            if on_action is not None:
                self.action_button.clicked.connect(on_action)

            layout.addWidget(
                self.action_button,
                0,
                Qt.AlignmentFlag.AlignCenter,
            )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_message(self, message: str):

        self.message_label.setText(message)
