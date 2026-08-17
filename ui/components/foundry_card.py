# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_card.py
#
# Purpose:
# Standard container used throughout the
# Foundry interface.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLayout,
)

from ui.theme.fonts import Fonts


class FoundryCard(QFrame):
    """
    Standard Foundry content card.

    +----------------------------------------+
    | 🪶 Title                               |
    |----------------------------------------|
    |                                        |
    |   Content                              |
    |                                        |
    +----------------------------------------+
    """

    def __init__(
        self,
        title: str = "",
        icon: str = "",
        parent=None,
    ):
        super().__init__(parent)

        #
        # Theme
        #

        self.setProperty(
            "foundryCard",
            True,
        )

        #
        # Header
        #

        self.header = QWidget()

        self.header.setProperty(
            "cardHeader",
            True,
        )

        header_layout = QHBoxLayout(self.header)

        header_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )

        header_layout.setSpacing(8)

        #
        # Icon
        #

        self.icon_label = QLabel(icon)

        self.icon_label.setProperty(
            "cardIcon",
            True,
        )

        #
        # Title
        #

        self.title_label = QLabel(title)

        self.title_label.setProperty(
            "cardTitle",
            True,
        )

        self.title_label.setFont(
            Fonts.section_title()
        )

        #
        # Badge / count (optional)
        #

        self.badge_label = QLabel("")

        self.badge_label.setProperty(
            "cardBadge",
            True,
        )

        self.badge_label.setVisible(False)

        header_layout.addWidget(
            self.icon_label
        )

        header_layout.addWidget(
            self.title_label
        )

        header_layout.addWidget(
            self.badge_label
        )

        header_layout.addStretch()

        #
        # Header action (optional)
        #
        # A caller-supplied widget (button, dropdown, ...)
        # docked to the right of the header, e.g. "+ Add
        # Note". Empty/absent by default.
        #

        self.header_action_layout = QHBoxLayout()

        self.header_action_layout.setContentsMargins(
            0, 0, 0, 0,
        )

        header_layout.addLayout(
            self.header_action_layout
        )

        #
        # Body
        #

        self.body = QWidget()

        self.body_layout = QVBoxLayout(
            self.body
        )

        self.body_layout.setContentsMargins(
            14, 14, 14, 14,
        )

        self.body_layout.setSpacing(8)

        #
        # Root
        #

        root = QVBoxLayout(self)

        root.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root.setSpacing(0)

        root.addWidget(
            self.header
        )

        root.addWidget(
            self.body
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_title(
        self,
        title: str,
    ):

        self.title_label.setText(title)

    def set_icon(
        self,
        icon: str,
    ):

        self.icon_label.setText(icon)

    def set_badge(
        self,
        text: str,
    ):
        """
        Small count/badge shown beside the title, e.g.
        "3 pending". Pass an empty string to hide it.
        """

        self.badge_label.setText(text)

        self.badge_label.setVisible(
            bool(text)
        )

    def set_header_action(
        self,
        widget: QWidget,
    ):
        """
        Dock a widget (button, dropdown, ...) to the
        right of the header, e.g. a "+ Add Note" button.
        Replaces any previously set header action.
        """

        while self.header_action_layout.count():

            item = self.header_action_layout.takeAt(0)

            if item.widget():
                item.widget().setParent(None)

        self.header_action_layout.addWidget(widget)

    def addWidget(
        self,
        widget: QWidget,
    ):

        self.body_layout.addWidget(widget)

    def addLayout(
        self,
        layout: QLayout,
    ):

        self.body_layout.addLayout(layout)

    def addStretch(
        self,
        stretch: int = 0,
    ):

        self.body_layout.addStretch(stretch)

    def clear(self):

        while self.body_layout.count():

            item = self.body_layout.takeAt(0)

            if item.widget():

                item.widget().deleteLater()

    
    