# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_progress_ring.py
#
# Purpose:
# Generic circular value/max indicator.
#
# Used both as a single large "fill" ring (e.g. role
# coverage 19/19) and repeated small along a timeline
# (phase threshold markers). Custom-painted, since Qt
# has no built-in ring widget.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QPropertyAnimation, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class FoundryProgressRing(QWidget):
    """
    A circular progress indicator with a centered label.

        FoundryProgressRing(value=19, maximum=19, label="Filled")
        FoundryProgressRing(value=75, maximum=100, size=Metrics.RING_SMALL,
                             color=Colors.ERROR, show_label=False)
    """

    def __init__(
        self,
        value: float = 0,
        maximum: float = 100,
        label: str = "",
        *,
        size: int = Metrics.RING,
        thickness: int = Metrics.RING_THICKNESS,
        color: str = Colors.GOLD,
        track_color: str = Colors.SURFACE_LIGHT,
        show_label: bool = True,
        animate: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self._maximum = maximum or 1
        self._value = 0.0
        self._display_value = 0.0
        self._label = label
        self._size = size
        self._thickness = thickness
        self._color = color
        self._track_color = track_color
        self._show_label = show_label
        self._animate = animate

        self.setFixedSize(size, size)

        self._animation = QPropertyAnimation(
            self, b"displayValue"
        )

        self._animation.setDuration(Metrics.NORMAL)

        self.set_value(value)

    # --------------------------------------------------
    # Animated value property
    # --------------------------------------------------

    def _get_display_value(self):
        return self._display_value

    def _set_display_value(self, v):
        self._display_value = v
        self.update()

    displayValue = Property(
        float, _get_display_value, _set_display_value
    )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_value(
        self,
        value: float,
        maximum: float | None = None,
    ):

        if maximum is not None:
            self._maximum = maximum or 1

        self._value = value

        if self._animate and self.isVisible():

            self._animation.stop()
            self._animation.setStartValue(self._display_value)
            self._animation.setEndValue(value)
            self._animation.start()

        else:

            self._display_value = value
            self.update()

    def set_label(
        self,
        label: str,
    ):

        self._label = label
        self.update()

    def set_color(
        self,
        color: str,
    ):

        self._color = color
        self.update()

    # --------------------------------------------------
    # Painting
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = QRectF(
            self._thickness / 2,
            self._thickness / 2,
            self._size - self._thickness,
            self._size - self._thickness,
        )

        # Track
        track_pen = QPen(
            QColor(self._track_color),
            self._thickness,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )

        painter.setPen(track_pen)

        painter.drawArc(rect, 0, 360 * 16)

        # Fill
        fraction = max(
            0.0,
            min(1.0, self._display_value / self._maximum),
        )

        fill_pen = QPen(
            QColor(self._color),
            self._thickness,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )

        painter.setPen(fill_pen)

        span = int(360 * 16 * fraction)

        painter.drawArc(rect, 90 * 16, -span)

        # Center label
        if self._show_label:

            painter.setPen(QColor(Colors.TEXT))

            font = Fonts.metric()

            font.setPointSize(
                max(8, int(self._size / 5.5))
            )

            painter.setFont(font)

            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                f"{int(self._value)}/{int(self._maximum)}",
            )
