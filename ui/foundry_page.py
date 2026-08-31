# ==================================================
# Black Feather Foundry
# ui/foundry_page.py
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QSizePolicy, QFrame


class FoundryPage(QWidget):
    """Standard Foundry page with one internal scrollable workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(10, 8, 10, 8)
        self.root.setSpacing(8)

        self.workspace_widget = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_widget)
        self.workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace_layout.setSpacing(8)
        self.workspace_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.workspace_scroll.setHorizontalScrollBarPolicy(
            self.workspace_scroll.horizontalScrollBarPolicy()
        )
        self.workspace_scroll.setWidget(self.workspace_widget)

        self.root.addWidget(self.workspace_scroll, 1)

        self.header = None
        self.actions = None
        self.status = None

    def set_header(self, widget):
        self.header = widget
        self.root.insertWidget(0, widget)

    def add_workspace(self, widget):
        self.workspace_layout.addWidget(widget, 1)

    def add_workspace_layout(self, layout):
        self.workspace_layout.addLayout(layout)

    def set_actions(self, widget):
        self.actions = widget
        self.root.addWidget(widget)

    def set_status(self, widget):
        self.status = widget
        self.root.addWidget(widget)
