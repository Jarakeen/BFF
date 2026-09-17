from __future__ import annotations

"""Place the Urban Wilderness Roster back control beside the top summary cards.

This keeps navigation visually attached to the Roster card strip while preserving the
full width of every embedded detail workspace below it.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QToolButton

from engine.config import get_resource_path

_BACK_ARROW = (
    "assets",
    "themes",
    "bff",
    "urban_wilderness",
    "roster",
    "back_arrow.png",
)


def install_roster_top_back_control(page) -> None:
    """Relocate Back into the top metric strip without narrowing detail content."""
    metrics = page.workspace_layout.itemAt(0).widget() if page.workspace_layout.count() else None
    metrics_layout = metrics.layout() if metrics is not None else None
    stack = getattr(page, "_embedded_stack", None)
    if metrics_layout is None or stack is None:
        return

    # Retire the per-detail side rails created by the compatibility wrapper.
    for button in page.findChildren(QToolButton):
        if bool(button.property("rosterBackButton")):
            button.hide()
            button.setEnabled(False)

    # Re-home only the six top cards. The embedded detail stack below is untouched.
    for column, card in enumerate(page.metric_cards.values(), start=1):
        metrics_layout.addWidget(card, 0, column)
        metrics_layout.setColumnStretch(column, 1)

    back = QToolButton(metrics)
    back.setObjectName("rosterTopBackButton")
    back.setProperty("rosterBackButton", True)
    back.setToolTip("Back to Roster")
    back.setAutoRaise(True)
    back.setFixedSize(58, 58)
    path = get_resource_path(*_BACK_ARROW)
    if Path(path).is_file():
        back.setIcon(QIcon(str(path)))
    back.setIconSize(QSize(52, 52))
    back.setStyleSheet(
        "QToolButton { background: transparent; border: none; padding: 0; } "
        "QToolButton:hover { background: rgba(200,164,106,20); border-radius: 6px; }"
    )
    back.clicked.connect(page._show_dashboard)
    metrics_layout.addWidget(back, 0, 0, Qt.AlignmentFlag.AlignCenter)
    metrics_layout.setColumnMinimumWidth(0, 62)
    metrics_layout.setColumnStretch(0, 0)

    def sync_visibility(index: int) -> None:
        back.setVisible(index != 0)

    stack.currentChanged.connect(sync_visibility)
    sync_visibility(stack.currentIndex())
    page.roster_top_back_button = back


__all__ = ["install_roster_top_back_control"]
