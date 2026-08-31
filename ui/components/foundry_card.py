# ==================================================
# Black Feather Foundry
# ui/components/foundry_card.py
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QFrame,
    QHBoxLayout,
    QLayout,
    QSizePolicy,
    QTableWidget,
    QTableView,
    QVBoxLayout,
)

from ui.theme.fonts import Fonts


class FoundryCard(QFrame):
    """Dense book-panel card used throughout the Foundry UI."""

    def __init__(self, title: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("foundryCard", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.header = QWidget()
        self.header.setProperty("cardHeader", True)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setMinimumHeight(30)
        self.header.setMaximumHeight(34)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 3, 8, 3)
        header_layout.setSpacing(6)

        self.icon_label = QLabel(icon)
        self.icon_label.setProperty("cardIcon", True)
        self.icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.title_label = QLabel(title)
        self.title_label.setProperty("cardTitle", True)
        self.title_label.setFont(Fonts.section_title())
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.badge_label = QLabel("")
        self.badge_label.setProperty("cardBadge", True)
        self.badge_label.setVisible(False)
        self.badge_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.badge_label)
        header_layout.addStretch()

        self.header_action_layout = QHBoxLayout()
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        self.header_action_layout.setSpacing(4)
        header_layout.addLayout(self.header_action_layout)

        self.body = QWidget()
        self.body.setProperty("cardBody", True)
        self.body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(10, 8, 10, 8)
        self.body_layout.setSpacing(5)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header, 0)
        root.addWidget(self.body, 1)

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

    def set_body_margins(self, left: int, top: int, right: int, bottom: int):
        self.body_layout.setContentsMargins(left, top, right, bottom)

    def set_body_spacing(self, spacing: int):
        self.body_layout.setSpacing(spacing)

    def make_table_card(self):
        self.setProperty("tableCard", True)
        self.body.setProperty("tableCardBody", True)
        self.set_body_margins(0, 0, 0, 0)
        self.set_body_spacing(0)
        self.style().unpolish(self)
        self.style().polish(self)
        return self

    def make_parchment(self):
        """Turn the whole card, including header/body, into one paper surface."""
        self.setProperty("parchment", True)
        self.style().unpolish(self)
        self.style().polish(self)
        return self

    def addWidget(self, widget: QWidget):
        if self.body_layout.count() == 0 and isinstance(widget, (QTableWidget, QTableView)):
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
