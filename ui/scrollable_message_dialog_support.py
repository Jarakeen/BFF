from __future__ import annotations

"""Keep long informational/error messages readable on ordinary screens.

Qt's convenience QMessageBox helpers size themselves from their text.  Large
import/audit diagnostics can therefore grow taller than the desktop and leave
the user unable to reach the useful part of the message.  Short messages keep
using the native QMessageBox behavior; only long/multiline messages are routed
through a resizable dialog with a read-only scrollable text area.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)


_INSTALLED = False
_ORIGINALS: dict[str, Callable[..., Any]] = {}
_LONG_MESSAGE_CHARACTERS = 700
_LONG_MESSAGE_LINES = 12


def _needs_scrollable_dialog(text: object) -> bool:
    value = str(text or "")
    return len(value) >= _LONG_MESSAGE_CHARACTERS or value.count("\n") + 1 >= _LONG_MESSAGE_LINES


class ScrollableMessageDialog(QDialog):
    """Resizable, theme-inheriting replacement for oversized message boxes."""

    def __init__(self, parent, title: str, text: str, *, kind: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(str(title or "Message"))
        self.setMinimumSize(520, 320)
        self.resize(760, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        heading = QLabel(
            {
                "warning": "Warning",
                "critical": "Error",
                "information": "Information",
            }.get(kind, "Message")
        )
        heading.setProperty("sidebarHeading", True)
        root.addWidget(heading)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(str(text or ""))
        body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        root.addWidget(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


def _show_scrollable(parent, title: str, text: str, *, kind: str):
    ScrollableMessageDialog(parent, title, text, kind=kind).exec()
    return QMessageBox.StandardButton.Ok


def _wrapper(kind: str, original: Callable[..., Any]):
    def wrapped(parent, title, text, *args, **kwargs):
        if _needs_scrollable_dialog(text):
            return _show_scrollable(parent, title, str(text or ""), kind=kind)
        return original(parent, title, text, *args, **kwargs)

    return wrapped


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    for name in ("information", "warning", "critical"):
        original = getattr(QMessageBox, name)
        _ORIGINALS[name] = original
        setattr(QMessageBox, name, staticmethod(_wrapper(name, original)))

    _INSTALLED = True
