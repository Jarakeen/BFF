from __future__ import annotations

"""Contextual Urban Wilderness Roster back control.

The bronze arrow belongs with the top Roster card strip. It appears only while a detail
workspace is active, may nudge that strip to the right, and never steals width from the
main detail content below.
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
    """Show Back beside the top summary cards only while a detail page is open."""
    stack = getattr(page, "_embedded_stack", None)
    metrics = page.workspace_layout.itemAt(0).widget() if page.workspace_layout.count() else None
    metrics_layout = metrics.layout() if metrics is not None else None
    if stack is None or metrics_layout is None:
        return

    # Remove the compatibility wrapper's per-detail side rail entirely. Hiding the
    # button alone still leaves a layout object hanging around like bad bureaucracy.
    for button in page.findChildren(QToolButton):
        if bool(button.property("rosterBackButton")):
            button.hide()
            button.setEnabled(False)
            button.deleteLater()

    for index in range(1, stack.count()):
        shell = stack.widget(index)
        layout = shell.layout() if shell is not None else None
        if layout is None:
            continue
        if layout.count() >= 2:
            first = layout.itemAt(0)
            if first is not None and first.layout() is not None:
                layout.takeAt(0)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

    # Re-home the six cards one column to the right. Column 0 collapses to zero
    # on the dashboard and opens only when the contextual back control is needed.
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
        "QToolButton:hover { background: rgba(200,164,106,24); border-radius: 6px; }"
    )
    back.clicked.connect(page._show_dashboard)
    metrics_layout.addWidget(back, 0, 0, Qt.AlignmentFlag.AlignCenter)
    metrics_layout.setColumnStretch(0, 0)

    def sync_visibility(index: int) -> None:
        visible = index != 0
        back.setVisible(visible)
        metrics_layout.setColumnMinimumWidth(0, 62 if visible else 0)

    stack.currentChanged.connect(sync_visibility)
    sync_visibility(stack.currentIndex())
    page.roster_top_back_button = back


__all__ = ["install_roster_top_back_control"]
