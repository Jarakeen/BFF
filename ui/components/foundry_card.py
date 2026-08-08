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
            Fonts.section()
        )

        header_layout.addWidget(
            self.icon_label
        )

        header_layout.addWidget(
            self.title_label
        )

        header_layout.addStretch()

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