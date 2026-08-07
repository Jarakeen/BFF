# ==================================================
# Black Feather Foundry
#
# File:
# ui/foundry_page.py
#
# Purpose:
# Base class for all Foundry pages.
#
# Provides a consistent page structure:
#
#   Header
#   -----------------------------
#   Scrollable Workspace
#   -----------------------------
#   Action Bar
#   Status Bar
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QSizePolicy,
)


class FoundryPage(QWidget):
    """
    Standard Foundry page layout.

    Header
    Scrollable Workspace
    Bottom Actions
    Status
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Root Layout
        #

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        self.root.setSpacing(12)

        #
        # Workspace
        #

        self.workspace_widget = QWidget()

        self.workspace_layout = QVBoxLayout(
            self.workspace_widget
        )

        self.workspace_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.workspace_layout.setSpacing(12)

        self.root.addWidget(
        self.workspace_widget,
        1,
        ) 
        #
        # References
        #

        self.header = None
        self.actions = None
        self.status = None

    # --------------------------------------------------
    # Header
    # --------------------------------------------------

    def set_header(self, widget):

        self.header = widget

        self.root.insertWidget(
            0,
            widget,
        )

    # --------------------------------------------------
    # Workspace
    # --------------------------------------------------

    def add_workspace(self, widget):

        self.workspace_layout.addWidget(
            widget
        )

    def add_workspace_layout(self, layout):

        self.workspace_layout.addLayout(
            layout
        )

    # --------------------------------------------------
    # Footer
    # --------------------------------------------------

    def set_actions(self, widget):

        self.actions = widget

        self.root.addWidget(
            widget
        )

    def set_status(self, widget):

        self.status = widget

        self.root.addWidget(
            widget
        )