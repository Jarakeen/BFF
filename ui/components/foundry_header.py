# ==================================================
# Black Feather Foundry
# ui/components/foundry_header.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy

from ui.theme.fonts import Fonts


class FoundryHeader(QWidget):
    """Compact page header with context controls docked to the right."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        department: str = "",
        icon: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("foundryHeader", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.icon = QLabel(icon)
        self.icon.setProperty("headerIcon", True)
        self.title = QLabel(title)
        self.title.setProperty("pageTitle", True)
        self.title.setFont(Fonts.page_title())
        self.subtitle = QLabel(subtitle)
        self.subtitle.setProperty("pageSubtitle", True)
        self.subtitle.setFont(Fonts.subtitle())
        self.subtitle.setWordWrap(False)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        title_row.addWidget(self.icon)
        title_row.addWidget(self.title)
        title_row.addStretch()

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(1)
        left.addLayout(title_row)
        left.addWidget(self.subtitle)

        self.department = QLabel(department.upper())
        self.department.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.department.setProperty("departmentLabel", True)

        self.context_layout = QHBoxLayout()
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setSpacing(10)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(3)
        right.addWidget(self.department)
        right.addLayout(self.context_layout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(16)
        layout.addLayout(left, 1)
        layout.addLayout(right)

    def add_context_widget(self, widget: QWidget):
        self.context_layout.addWidget(widget)
