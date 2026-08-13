# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_timeline.py
#
# Purpose:
# Generic connected list of markers.
#
# Covers both a percent-based vertical phase list
# (100% -> 0%) and a time-stamped event list -- one
# data-driven component, not two. Each event is a plain
# dict; the timeline has no idea what a "trial phase" is.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_status_badge import FoundryStatusBadge
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class _Marker(QWidget):
    """A single dot, painted at a fixed width column."""

    def __init__(self, color: str, filled: bool = True, parent=None):
        super().__init__(parent)

        self._color = color
        self._filled = filled

        self.setFixedWidth(24)

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        cx = self.width() / 2
        cy = self.height() / 2
        r = 6

        # connecting line above/below, drawn by the
        # timeline container's own paint via stylesheet
        # border on the wrapping widget -- see FoundryTimeline

        pen = QPen(QColor(self._color), 2)

        painter.setPen(pen)

        if self._filled:
            painter.setBrush(QColor(self._color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawEllipse(
            QRectF(cx - r, cy - r, r * 2, r * 2)
        )


class FoundryTimeline(QWidget):
    """
    A vertical connected list of events.

        FoundryTimeline([
            {"marker": "100%", "label": "Phase 1", "detail": "Standard rotation.",
             "color": Colors.SUCCESS},
            {"marker": "25%", "label": "Execute", "detail": "Crushing Darkness begins.",
             "color": Colors.ERROR, "status": "blocked"},
        ])

    Each event dict:
      marker  - short text beside the dot (percent, time, ...)
      label   - bold title
      detail  - supporting text (optional)
      color   - dot/line color (optional, defaults to gold)
      status  - optional scale/key badge shown after the label
                (uses Colors.STATUS by default)
    """

    def __init__(
        self,
        events: list[dict] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)

        self._layout.setContentsMargins(0, 0, 0, 0)

        self._layout.setSpacing(0)

        self.set_events(events or [])

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_events(
        self,
        events: list[dict],
    ):

        while self._layout.count():

            item = self._layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        for i, event in enumerate(events):

            self._layout.addWidget(
                self._build_row(
                    event,
                    is_last=(i == len(events) - 1),
                )
            )

    # --------------------------------------------------
    # Row construction
    # --------------------------------------------------

    def _build_row(
        self,
        event: dict,
        is_last: bool,
    ) -> QWidget:

        from PySide6.QtWidgets import QHBoxLayout, QFrame

        color = event.get("color", Colors.GOLD)

        row = QWidget()

        row_layout = QHBoxLayout(row)

        row_layout.setContentsMargins(0, 4, 0, 4)

        row_layout.setSpacing(10)

        # Marker column: dot + connecting line
        marker_col = QWidget()

        marker_col.setFixedWidth(24)

        marker_layout = QVBoxLayout(marker_col)

        marker_layout.setContentsMargins(0, 0, 0, 0)

        marker_layout.setSpacing(0)

        dot = _Marker(color)

        dot.setFixedHeight(16)

        marker_layout.addWidget(dot)

        if not is_last:

            line = QFrame()

            line.setFrameShape(QFrame.Shape.VLine)

            line.setFixedWidth(24)

            line.setStyleSheet(
                f"color: {Colors.BORDER}; "
                f"margin-left: 11px;"
            )

            marker_layout.addWidget(line, 1)

        else:

            marker_layout.addStretch()

        row_layout.addWidget(marker_col)

        # Content column
        content = QVBoxLayout()

        content.setSpacing(2)

        header = QLabel(
            f"{event.get('marker', '')}  {event.get('label', '')}".strip()
        )

        header.setFont(
            Fonts.section_title()
        )

        header.setStyleSheet(
            f"color: {color};"
        )

        content.addWidget(header)

        if event.get("detail"):

            detail = QLabel(event["detail"])

            detail.setWordWrap(True)

            detail.setFont(Fonts.body())

            detail.setStyleSheet(
                f"color: {Colors.TEXT_MUTED};"
            )

            content.addWidget(detail)

        if event.get("status"):

            badge = FoundryStatusBadge(
                event["status"].replace("_", " ").title(),
                scale="status",
                key=event["status"],
            )

            content.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        row_layout.addLayout(content, 1)

        return row
