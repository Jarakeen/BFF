from __future__ import annotations

"""Contextual Urban Wilderness Roster back control.

The bronze arrow belongs to the detail workspace itself, but it must not consume layout
width. It therefore floats over the far-left edge of the embedded Roster stack and only
appears while a detail page is active.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize
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


class _BackArrowAnchor(QObject):
    """Keep a floating arrow vertically centered without changing page geometry."""

    def __init__(self, stack, button: QToolButton) -> None:
        super().__init__(stack)
        self.stack = stack
        self.button = button
        stack.installEventFilter(self)
        self.reposition()

    def reposition(self) -> None:
        x = 4
        y = max(4, (self.stack.height() - self.button.height()) // 2)
        self.button.move(x, y)
        self.button.raise_()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.stack and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            self.reposition()
        return False


def install_roster_top_back_control(page) -> None:
    """Overlay Back on detail views without narrowing any Roster content."""
    stack = getattr(page, "_embedded_stack", None)
    if stack is None:
        return

    # Retire the compatibility wrapper's old per-detail side controls. Their
    # containing layouts collapse after the buttons are hidden, returning the
    # detail workspace to its full available width.
    for button in page.findChildren(QToolButton):
        if bool(button.property("rosterBackButton")):
            button.hide()
            button.setEnabled(False)
            parent = button.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().setContentsMargins(0, 0, 0, 0)

    for index in range(1, stack.count()):
        shell = stack.widget(index)
        layout = shell.layout() if shell is not None else None
        if layout is not None:
            layout.setSpacing(0)

    back = QToolButton(stack)
    back.setObjectName("rosterContextBackButton")
    back.setProperty("rosterBackButton", True)
    back.setToolTip("Back to Roster")
    back.setAutoRaise(True)
    back.setFixedSize(52, 52)
    path = get_resource_path(*_BACK_ARROW)
    if Path(path).is_file():
        back.setIcon(QIcon(str(path)))
    back.setIconSize(QSize(46, 46))
    back.setStyleSheet(
        "QToolButton { background: rgba(7,18,22,150); border: none; padding: 0; } "
        "QToolButton:hover { background: rgba(200,164,106,28); border-radius: 6px; }"
    )
    back.clicked.connect(page._show_dashboard)

    anchor = _BackArrowAnchor(stack, back)

    def sync_visibility(index: int) -> None:
        visible = index != 0
        back.setVisible(visible)
        if visible:
            anchor.reposition()

    stack.currentChanged.connect(sync_visibility)
    sync_visibility(stack.currentIndex())
    page.roster_context_back_button = back
    page.roster_context_back_anchor = anchor


__all__ = ["install_roster_top_back_control"]
