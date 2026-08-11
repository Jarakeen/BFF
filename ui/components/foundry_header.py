# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_header.py
#
# Purpose:
# Standard page header.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

from ui.theme.fonts import Fonts


class FoundryHeader(QWidget):
    """
    Standard page header.

    +------------------------------------------------------+
    | 🪶 Title                         DEPARTMENT           |
    | Subtitle                                           |
    +------------------------------------------------------+
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        department: str = "",
        icon: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryHeader",
            True,
        )
        #
        # Left
        #

        self.icon = QLabel(icon)

        self.icon.setProperty(
            "headerIcon",
            True,
        )

        self.title = QLabel(title)

        self.title.setProperty(
            "pageTitle",
            True,
        )

        self.title.setFont(
            Fonts.page_title()
        )

        self.subtitle = QLabel(subtitle)

        self.subtitle.setProperty(
            "pageSubtitle",
            True,
        )

        self.subtitle.setWordWrap(True)

        left = QVBoxLayout()

        title_row = QHBoxLayout()

        title_row.setSpacing(8)

        title_row.addWidget(self.icon)

        title_row.addWidget(self.title)

        title_row.addStretch()

        left.addLayout(title_row)

        left.addWidget(self.subtitle)

        #
        # Right
        #

        self.department = QLabel(
            department.upper()
        )

        self.department.setAlignment(
            Qt.AlignRight | Qt.AlignTop
        )

        self.department.setProperty(
            "departmentLabel",
            True,
        )

        #
        # Context (optional)
        #
        # Extra widgets docked to the right of the header --
        # trial/boss selectors, a directive banner, and so
        # on. Empty by default; existing callers that only
        # pass `department` are unaffected.
        #

        self.context_layout = QHBoxLayout()

        self.context_layout.setContentsMargins(
            0, 0, 0, 0,
        )

        self.context_layout.setSpacing(12)

        right = QVBoxLayout()

        right.setSpacing(8)

        right.addWidget(
            self.department
        )

        right.addLayout(
            self.context_layout
        )

        #
        # Root
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            16,
        )

        layout.setSpacing(20)

        layout.addLayout(
            left,
            1,
        )

        layout.addLayout(
            right
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def add_context_widget(
        self,
        widget: QWidget,
    ):
        """
        Dock a widget (a filter dropdown, a directive
        banner, ...) to the right of the header, below
        the department label.
        """

        self.context_layout.addWidget(widget)