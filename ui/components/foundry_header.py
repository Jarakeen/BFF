# ==================================================
# Black Feather Foundry
# ui/components/foundry_header.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.theme.fonts import Fonts
from ui.ux_icons import icon as themed_icon, semantic_icon


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

        self._icon_name = icon or semantic_icon(title)
        self.icon = QLabel()
        self.icon.setProperty("headerIcon", True)
        self.icon.setFixedSize(24, 24)
        self.icon.setScaledContents(True)
        self._set_icon(self._icon_name)

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
        self.department.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.department.setProperty("departmentLabel", True)

        # Foundry keeps its small north-star ornament. Rylo deliberately omits
        # the gold fantasy ornament and lets the steel semantic page icon carry
        # the header identity instead.
        self.header_star = QLabel()
        self.header_star.setProperty("headerStar", True)
        self.header_star.setFixedSize(18, 18)
        self.header_star.setScaledContents(True)
        self._refresh_header_star()

        department_row = QHBoxLayout()
        department_row.setContentsMargins(0, 0, 0, 0)
        department_row.setSpacing(5)
        department_row.addStretch(1)
        department_row.addWidget(self.department, 0, Qt.AlignmentFlag.AlignVCenter)
        department_row.addWidget(self.header_star, 0, Qt.AlignmentFlag.AlignVCenter)

        self.context_layout = QHBoxLayout()
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setSpacing(10)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(3)
        right.addLayout(department_row)
        right.addLayout(self.context_layout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(16)
        layout.addLayout(left, 1)
        layout.addLayout(right)

    @staticmethod
    def _is_rylo() -> bool:
        app = QApplication.instance()
        return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)

    def _set_icon(self, name: str):
        self.icon.clear()
        self.icon.setVisible(bool(name))
        if not name:
            return
        value = themed_icon(name)
        if value.isNull():
            return
        self.icon.setPixmap(value.pixmap(24, 24))
        self.icon.setToolTip(name.replace("-", " ").title())
        self.icon.setProperty("semanticIconName", name)

    def _refresh_header_star(self) -> None:
        self.header_star.clear()
        if self._is_rylo():
            self.header_star.setVisible(False)
            return

        star_path = get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets", "header_star.svg"
        )
        if star_path.exists():
            star = QPixmap(str(star_path))
            if not star.isNull():
                self.header_star.setPixmap(star)
        self.header_star.setVisible(not self.header_star.pixmap().isNull())

    def refresh_visual_theme(self) -> None:
        self._set_icon(self._icon_name)
        self._refresh_header_star()

    def add_context_widget(self, widget: QWidget):
        self.context_layout.addWidget(widget)
