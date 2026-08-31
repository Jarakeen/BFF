from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton, QWidget

from engine.config import get_resource_path


_ICON_ROOTS = (
    ("assets", "icon"),
    ("assets", "icons"),
    ("assets", "themes", "bff", "icons"),
)


def icon_path(name: str) -> Path | None:
    """Resolve a named SVG from the user's icon library, with safe fallbacks."""
    if not name:
        return None
    filename = name if name.lower().endswith(".svg") else f"{name}.svg"
    for parts in _ICON_ROOTS:
        candidate = get_resource_path(*parts, filename)
        if candidate.exists():
            return candidate
    return None


def icon(name: str) -> QIcon:
    path = icon_path(name)
    return QIcon(str(path)) if path is not None else QIcon()


def set_button_icon(button: QPushButton | QToolButton, name: str, size: int = 16) -> None:
    value = icon(name)
    if value.isNull():
        return
    button.setIcon(value)
    button.setIconSize(QSize(size, size))


def icon_label(name: str, size: int = 18, parent: QWidget | None = None) -> QLabel:
    label = QLabel(parent)
    label.setFixedSize(size, size)
    label.setScaledContents(True)
    path = icon_path(name)
    if path is not None:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            label.setPixmap(pixmap)
    return label
