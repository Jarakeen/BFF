from __future__ import annotations

"""Urban Wilderness Roster entry point and final composition polish.

The underlying themed roster page owns canonical data and actions. This wrapper keeps
those data owners intact while presenting the approved single-window Roster flow: six
summary cards across the top, then either the dashboard or the selected roster detail
workspace directly underneath. No modal editor windows are used on this surface.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage
from ui.urban_wilderness_accessibility_polish import install as install_urban_wilderness_accessibility_polish
from ui.ux_icons import icon, set_button_icon


_BADGES = {
    "players": "users",
    "characters": "character",
    "teams": "users",
    "availability": "stopwatch",
    "recruitment": "person",
    "archive": "archive",
}


class _StaticRosterArt(QLabel):
    """Existing low-stimulation WebP art reused without animation or brightness effects."""

    def __init__(self, filename: str, parent=None) -> None:
        super().__init__(parent)
        self.filename = filename
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("rosterSketch", True)
        self.refresh()

    def refresh(self) -> None:
        # The field-journal JPG copies are intentionally avoided here. Some of
        # those files trigger libjpeg marker warnings in Qt. The equivalent
        # lightweight WebP assets are stable and cheaper to repaint on resize.
        path = get_resource_path(
            "assets", "themes", "bff", "city_night", "roster", self.filename
        )
        pixmap = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
        self.clear()
        if pixmap.isNull():
            self.setText("Leave better records.")
            return
        self.setPixmap(
            pixmap.scaled(
                max(300, self.width() or 420),
                max(120, self.height() or 170),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.refresh()


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """Compatibility route name for the single Urban Wilderness Roster dashboard."""

    def __init__(self, parent=None) -> None:
        install_urban_wilderness_accessibility_polish()
        self._embedded_detail_indexes: dict[str, int] = {}
        self._embedded_stack: QStackedWidget | None = None
        super().__init__(parent)
        self._replace_legacy_city_art()
        self._polish_urban_wilderness_roster()
        self._embed_detail_workspaces()

    def _replace_legacy_city_art(self) -> None:
        """Replace the old panels with stable Urban Wilderness city art."""
        for attribute, filename in (
            ("quote_art", "roster_people.webp"),
            ("team_art", "roster_team.webp"),
        ):
            old = getattr(self, attribute, None)
            if old is None:
                continue
            parent = old.parentWidget()
            layout = parent.layout() if parent is not None else None
            if layout is None:
                continue
            replacement = _StaticRosterArt(filename, parent)
            layout.replaceWidget(old, replacement)
            old.hide()
            old.deleteLater()
            setattr(self, attribute, replacement)

    def _polish_urban_wilderness_roster(self) -> None:
        """Keep the mockup readable at normal desktop widths without horizontal sprawl."""
        self.header.subtitle.setText("Same people. Different rooftops. Better runs.")
        self.header._set_icon("feather")

        for key, card in self.metric_cards.items():
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setMinimumHeight(132)
            card.setMaximumHeight(148)

            badge = next(
                (
                    label
                    for label in card.findChildren(QLabel)
                    if bool(label.property("rosterMetricIcon"))
                ),
                None,
            )
            if badge is not None:
                badge.clear()
                badge.setFixedSize(QSize(54, 54))
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setPixmap(icon(_BADGES.get(key, "compass")).pixmap(46, 46))
                badge.setProperty("rosterMetricBadge", True)

        if hasattr(self, "quote_art"):
            self.quote_art.setMinimumWidth(0)
            self.quote_art.setMaximumWidth(390)
            self.quote_art.setMinimumHeight(165)
            self.quote_art.setMaximumHeight(220)
        if hasattr(self, "team_art"):
            self.team_art.setMinimumWidth(0)
            self.team_art.setMaximumWidth(460)
            self.team_art.setMinimumHeight(120)
            self.team_art.setMaximumHeight(160)

        if hasattr(self, "table"):
            header = self.table.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for column, width in enumerate((190, 165, 110, 120, 120, 130, 105)):
                self.table.setColumnWidth(column, width)
            self.table.setMinimumWidth(720)

        if hasattr(self, "team_snapshot_label"):
            self.team_snapshot_label.setToolTip(
                "Good people make hard things possible. Different rooftops. Same horizon."
            )

    def _embed_detail_workspaces(self) -> None:
        """Move legacy dialog-owned editors into one in-page stack beneath the card bar."""
        if self.workspace_layout.count() < 2:
            return

        dashboard_item = self.workspace_layout.takeAt(1)
        dashboard = dashboard_item.widget()
        if dashboard is None:
            return

        stack = QStackedWidget()
        stack.setProperty("rosterEmbeddedWorkspace", True)
        stack.addWidget(dashboard)
        self._embedded_stack = stack

        for key, dialog in list(self._detail_dialogs.items()):
            dialog_layout = dialog.layout()
            if dialog_layout is None or dialog_layout.count() == 0:
                continue
            item = dialog_layout.takeAt(0)
            page = item.widget()
            if page is None:
                continue
            page.setParent(None)

            shell = QWidget()
            shell_layout = QVBoxLayout(shell)
            shell_layout.setContentsMargins(0, 0, 0, 0)
            shell_layout.setSpacing(8)

            nav = QHBoxLayout()
            back = QPushButton("Back to Roster")
            set_button_icon(back, "back")
            back.clicked.connect(self._show_dashboard)
            nav.addWidget(back)
            nav.addStretch(1)
            shell_layout.addLayout(nav)
            shell_layout.addWidget(page, 1)

            index = stack.addWidget(shell)
            self._embedded_detail_indexes[key] = index
            dialog.close()
            dialog.deleteLater()

        self._detail_dialogs.clear()
        self.workspace_layout.insertWidget(1, stack, 1)
        stack.setCurrentIndex(0)

    def _show_dashboard(self) -> None:
        if self._embedded_stack is not None:
            self._embedded_stack.setCurrentIndex(0)

    def _show_detail(self, key: str) -> None:
        """Open Players/Characters/Teams/etc. in-page instead of as a pop-up."""
        if self._embedded_stack is not None:
            index = self._embedded_detail_indexes.get(key)
            if index is not None:
                self._embedded_stack.setCurrentIndex(index)
                return
        super()._show_detail(key)


__all__ = ["CityRaidRosterWorkspacePage"]
