# ==================================================
# Black Feather Foundry
# ui/components/foundry_header.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy

from engine.config import get_resource_path
from ui.theme.fonts import Fonts
from ui.ux_icons import icon_path, semantic_icon


class FoundryHeader(QWidget):
    """Compact page header with semantic asset icon and right-side context controls."""

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

        self._header_star = QPixmap()
        star_path = get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets", "header_star.svg"
        )
        if star_path.exists():
            star = QPixmap(str(star_path))
            if not star.isNull():
                self._header_star = star

        self.icon = QLabel()
        self.icon.setProperty("headerIcon", True)
        self.icon.setFixedSize(24, 24)
        self.icon.setScaledContents(True)
        self._set_icon(icon or semantic_icon(title))

        self.title = QLabel(title)
        self.title.setProperty("pageTitle", True)
        self.title.setFont(Fonts.page_title())
        self.subtitle = QLabel(subtitle)
        self.subtitle.setProperty("pageSubtitle", True)
        self.subtitle.setFont(Fonts.subtitle())
        self.subtitle.setWordWrap(False)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(7)
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
        # Reserve a little room for the brass north-star ornament so the
        # department label reads like the mockup's ARCHIVES + star treatment.
        self.department.setContentsMargins(0, 0, 25, 0)

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

    def _set_icon(self, name: str):
        self.icon.clear()
        self.icon.setVisible(bool(name))
        if not name:
            return
        path = icon_path(name)
        if path is None:
            return
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self.icon.setPixmap(pixmap)
            self.icon.setToolTip(name.replace("-", " ").title())

    def add_context_widget(self, widget: QWidget):
        self.context_layout.addWidget(widget)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._header_star.isNull() or not self.department.text().strip():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # The ornament belongs to the page-context label, not the page title.
        # Draw it just inside the upper-right edge so it appears tucked behind
        # and beside the department text, matching the reference mockup.
        star = self._header_star
        target = 24
        if star.width() != target or star.height() != target:
            star = star.scaled(
                target,
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        x = max(0, self.width() - star.width() - 1)
        dept_y = self.department.mapTo(self, self.department.rect().topLeft()).y()
        y = max(0, dept_y - 4)

        painter.setOpacity(0.88)
        painter.drawPixmap(x, y, star)
        painter.end()
