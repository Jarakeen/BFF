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

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QFrame,
    QHBoxLayout,
    QLayout,
    QTableWidget,
    QTableView,
    QVBoxLayout,
)

from ui.theme.fonts import Fonts


class FoundryCard(QFrame):
    """Standard Foundry content card."""

    def __init__(
        self,
        title: str = "",
        icon: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty("foundryCard", True)

        self.header = QWidget()
        self.header.setProperty("cardHeader", True)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self.icon_label = QLabel(icon)
        self.icon_label.setProperty("cardIcon", True)

        self.title_label = QLabel(title)
        self.title_label.setProperty("cardTitle", True)
        self.title_label.setFont(Fonts.section_title())

        self.badge_label = QLabel("")
        self.badge_label.setProperty("cardBadge", True)
        self.badge_label.setVisible(False)

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.badge_label)
        header_layout.addStretch()

        self.header_action_layout = QHBoxLayout()
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addLayout(self.header_action_layout)

        self.body = QWidget()
        self.body.setProperty("cardBody", True)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(14, 14, 14, 14)
        self.body_layout.setSpacing(8)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addWidget(self.body)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_icon(self, icon: str):
        self.icon_label.setText(icon)

    def set_badge(self, text: str):
        self.badge_label.setText(text)
        self.badge_label.setVisible(bool(text))

    def set_header_action(self, widget: QWidget):
        while self.header_action_layout.count():
            item = self.header_action_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.header_action_layout.addWidget(widget)

    def set_body_margins(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ):
        """Adjust body padding for special content such as flush tables."""
        self.body_layout.setContentsMargins(left, top, right, bottom)

    def set_body_spacing(self, spacing: int):
        """Adjust spacing between body children."""
        self.body_layout.setSpacing(spacing)

    def make_table_card(self):
        """Make the body behave like an integrated table panel."""
        self.setProperty("tableCard", True)
        self.body.setProperty("tableCardBody", True)
        self.set_body_margins(0, 0, 0, 0)
        self.set_body_spacing(0)
        self.style().unpolish(self)
        self.style().polish(self)
        return self

    def addWidget(self, widget: QWidget):
        # Tables are structural content in the Foundry UI. When a table is
        # the first body widget, let it meet the card frame rather than
        # floating inside a second padded rectangle. The table itself loses
        # its outer frame so the card border becomes the visual frame.
        if (
            self.body_layout.count() == 0
            and isinstance(widget, (QTableWidget, QTableView))
        ):
            self.make_table_card()
            widget.setFrameShape(QFrame.NoFrame)
            widget.setLineWidth(0)

        self.body_layout.addWidget(widget)

    def addLayout(self, layout: QLayout):
        self.body_layout.addLayout(layout)

    def addStretch(self, stretch: int = 0):
        self.body_layout.addStretch(stretch)

    def clear(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
