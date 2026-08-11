# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_icon.py
#
# Purpose:
# Semantic, recolorable SVG icons.
#
# Loads a single-color outline icon from assets/icons/
# and tints it to any Colors value at any Metrics size,
# rather than baking a bitmap per color per icon.
#
# Decorative brand artwork (assets/themes/bff/decorative)
# is NOT served by this component -- those are static
# marks, not semantic/recolorable icons.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

from ui.theme.colors import Colors
from ui.theme.metrics import Metrics

ICONS_DIR = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "icons"
)

# (name, size, color) -> QPixmap
_CACHE: dict[tuple[str, int, str], QPixmap] = {}


def available_icons() -> list[str]:
    """Names of every icon currently on disk."""

    if not ICONS_DIR.exists():
        return []

    return sorted(
        p.stem for p in ICONS_DIR.glob("*.svg")
    )


def _render_pixmap(
    name: str,
    size: int,
    color: str,
) -> QPixmap:

    key = (name, size, color)

    cached = _CACHE.get(key)

    if cached is not None:
        return cached

    path = ICONS_DIR / f"{name}.svg"

    pixmap = QPixmap(size, size)

    pixmap.fill(Qt.GlobalColor.transparent)

    if path.exists():

        renderer = QSvgRenderer(str(path))

        painter = QPainter(pixmap)

        renderer.render(painter)

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceIn
        )

        painter.fillRect(
            pixmap.rect(),
            QColor(color),
        )

        painter.end()

    _CACHE[key] = pixmap

    return pixmap


class FoundryIcon(QLabel):
    """
    A single recolorable icon, embeddable anywhere a
    QLabel/QWidget is accepted.

        FoundryIcon("boss", size=Metrics.ICON, color=Colors.GOLD)

    Also exposes static helpers for contexts that need a
    QPixmap or QIcon directly (table cells, buttons,
    custom-painted widgets) instead of a widget.
    """

    def __init__(
        self,
        name: str,
        size: int = Metrics.ICON,
        color: str = Colors.TEXT,
        parent=None,
    ):
        super().__init__(parent)

        self._name = name

        self._size = size

        self._color = color

        self.setFixedSize(
            QSize(size, size)
        )

        self._refresh()

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_icon(
        self,
        name: str,
    ):

        self._name = name

        self._refresh()

    def set_color(
        self,
        color: str,
    ):

        self._color = color

        self._refresh()

    def set_size(
        self,
        size: int,
    ):

        self._size = size

        self.setFixedSize(
            QSize(size, size)
        )

        self._refresh()

    # --------------------------------------------------
    # Static helpers
    # --------------------------------------------------

    @staticmethod
    def render_pixmap(
        name: str,
        size: int = Metrics.ICON,
        color: str = Colors.TEXT,
    ) -> QPixmap:

        return _render_pixmap(name, size, color)

    @staticmethod
    def to_icon(
        name: str,
        size: int = Metrics.ICON,
        color: str = Colors.TEXT,
    ) -> QIcon:

        return QIcon(
            FoundryIcon.render_pixmap(name, size, color)
        )

    # --------------------------------------------------
    # Internal
    # --------------------------------------------------

    def _refresh(self):

        self.setPixmap(
            _render_pixmap(
                self._name,
                self._size,
                self._color,
            )
        )
