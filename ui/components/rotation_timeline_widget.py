from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from engine.config import get_resource_path
from services.rotation_timeline_projection_service import (
    RotationTimelineAction,
    RotationTimelineLane,
    RotationTimelineProjection,
)


class _RotationTimelineCanvas(QWidget):
    LEFT_MARGIN = 18
    RIGHT_MARGIN = 24
    TOP_MARGIN = 14
    ICON_SIZE = 38
    ICON_ROW_HEIGHT = 58
    AXIS_HEIGHT = 24
    LANE_HEIGHT = 22
    LANE_GAP = 6
    PIXELS_PER_SECOND = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projection: RotationTimelineProjection | None = None
        self._icon_rects: list[tuple[QRectF, RotationTimelineAction]] = []
        self._segment_rects: list[tuple[QRectF, RotationTimelineLane, float, float]] = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self._refresh_size()

    def set_projection(self, projection: RotationTimelineProjection | None) -> None:
        self._projection = projection
        self._refresh_size()
        self.update()

    def _refresh_size(self) -> None:
        projection = self._projection
        duration = float(projection.duration_seconds) if projection is not None else 60.0
        lanes = len(projection.lanes) if projection is not None else 0
        width = int(
            self.LEFT_MARGIN
            + max(1.0, duration) * self.PIXELS_PER_SECOND
            + self.RIGHT_MARGIN
        )
        height = (
            self.TOP_MARGIN
            + self.ICON_ROW_HEIGHT
            + self.AXIS_HEIGHT
            + max(1, lanes) * (self.LANE_HEIGHT + self.LANE_GAP)
            + 20
        )
        self.setMinimumSize(QSize(max(640, width), max(170, height)))
        self.resize(self.minimumSize())

    def _time_x(self, seconds: float) -> float:
        return self.LEFT_MARGIN + float(seconds) * self.PIXELS_PER_SECOND

    def _lane_color(self, index: int) -> QColor:
        palette = self.palette()
        candidates = [
            palette.highlight().color(),
            palette.link().color(),
            QColor(111, 167, 109),
            QColor(200, 155, 90),
            QColor(92, 142, 199),
            QColor(201, 106, 106),
        ]
        color = QColor(candidates[index % len(candidates)])
        if color.alpha() < 190:
            color.setAlpha(220)
        return color

    @staticmethod
    def _candidate_icon_paths(action: RotationTimelineAction) -> tuple[Path, ...]:
        key = action.icon_key
        return tuple(
            get_resource_path(*parts)
            for parts in (
                ("assets", "AbilityIcons", "icons", "128", f"{key}.png"),
                ("assets", "ability_icons", f"{key}.png"),
                ("assets", "AbilityIcons", f"{key}.png"),
                ("assets", "icons", "skills", f"{key}.png"),
                ("assets", "icons", "abilities", f"{key}.png"),
            )
        )

    @classmethod
    def _pixmap_from_icon_path(cls, path: str | Path) -> QPixmap | None:
        """Load one ability icon using the same QIcon path as the Build editor."""
        icon = QIcon(str(path))
        if icon.isNull():
            return None
        pixmap = icon.pixmap(QSize(cls.ICON_SIZE, cls.ICON_SIZE))
        return None if pixmap.isNull() else pixmap

    @classmethod
    def _icon_pixmap(cls, action: RotationTimelineAction) -> QPixmap | None:
        explicit = str(action.icon_path or "").strip()
        if explicit:
            pixmap = cls._pixmap_from_icon_path(explicit)
            if pixmap is not None:
                return pixmap

        # Last-resort compatibility lookup for any older projection that does not
        # yet carry an explicit resolved icon path. This is intentionally path-only;
        # database/name resolution belongs before painting.
        for path in cls._candidate_icon_paths(action):
            if not path.exists():
                continue
            pixmap = cls._pixmap_from_icon_path(path)
            if pixmap is not None:
                return pixmap
        return None

    @staticmethod
    def _fallback_initials(name: str) -> str:
        words = [word for word in str(name).replace("-", " ").split() if word]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return "".join(word[0] for word in words[:2]).upper()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._icon_rects = []
        self._segment_rects = []

        projection = self._projection
        text = self.palette().text().color()
        muted = QColor(text)
        muted.setAlpha(115)
        grid = QColor(text)
        grid.setAlpha(36)
        surface = self.palette().base().color()
        alternate = self.palette().alternateBase().color()

        if projection is None:
            painter.setPen(muted)
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignmentFlag.AlignCenter,
                "Generate a rotation to view the timeline",
            )
            painter.end()
            return

        axis_y = self.TOP_MARGIN + self.ICON_ROW_HEIGHT
        lane_top = axis_y + self.AXIS_HEIGHT

        max_second = max(0, int(projection.duration_seconds))
        for second in range(0, max_second + 1):
            x = self._time_x(second)
            if second % 5 == 0:
                painter.setPen(QPen(grid, 1))
                painter.drawLine(QPointF(x, axis_y - 4), QPointF(x, self.height() - 10))
                painter.setPen(muted)
                painter.drawText(
                    QRectF(x - 18, axis_y, 36, 18),
                    Qt.AlignmentFlag.AlignCenter,
                    f"{second}s",
                )
            else:
                painter.setPen(QPen(grid, 1))
                painter.drawLine(QPointF(x, axis_y + 10), QPointF(x, axis_y + 15))

        for index, lane in enumerate(projection.lanes):
            y = lane_top + index * (self.LANE_HEIGHT + self.LANE_GAP)
            lane_rect = QRectF(
                self.LEFT_MARGIN,
                y,
                max(1.0, projection.duration_seconds) * self.PIXELS_PER_SECOND,
                self.LANE_HEIGHT,
            )
            painter.fillRect(lane_rect, alternate if index % 2 else surface)
            color = self._lane_color(index)
            for segment in lane.segments:
                rect = QRectF(
                    self._time_x(segment.start_seconds),
                    y + 3,
                    max(
                        3.0,
                        (segment.end_seconds - segment.start_seconds)
                        * self.PIXELS_PER_SECOND,
                    ),
                    self.LANE_HEIGHT - 6,
                )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(rect, 4, 4)
                self._segment_rects.append(
                    (rect, lane, segment.start_seconds, segment.end_seconds)
                )

        for action in projection.actions:
            x = self._time_x(action.time_seconds)
            rect = QRectF(
                x - self.ICON_SIZE / 2,
                self.TOP_MARGIN,
                self.ICON_SIZE,
                self.ICON_SIZE,
            )
            pixmap = self._icon_pixmap(action)
            if pixmap is not None:
                painter.drawPixmap(rect.toRect(), pixmap)
            else:
                fill = QColor(self.palette().highlight().color())
                fill.setAlpha(170)
                painter.setPen(QPen(self.palette().mid().color(), 1))
                painter.setBrush(fill)
                painter.drawRoundedRect(rect, 5, 5)
                painter.setPen(self.palette().highlightedText().color())
                metrics = QFontMetrics(painter.font())
                initials = self._fallback_initials(action.name)
                painter.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignCenter,
                    metrics.elidedText(
                        initials,
                        Qt.TextElideMode.ElideRight,
                        int(rect.width() - 4),
                    ),
                )

            painter.setPen(QPen(self.palette().mid().color(), 1))
            painter.drawRoundedRect(rect, 5, 5)
            self._icon_rects.append((rect, action))

        if not projection.lanes:
            painter.setPen(muted)
            painter.drawText(
                QRectF(
                    self.LEFT_MARGIN,
                    lane_top + 6,
                    max(320, self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN),
                    28,
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "Duration bars will appear when canonical positive-duration evidence is available.",
            )

        painter.end()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        point = event.position()
        for rect, action in self._icon_rects:
            if rect.contains(point):
                bar = (action.bar or "any").title()
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{action.name}\n{action.time_seconds:g}s • {bar} • {action.kind.replace('_', ' ').title()}",
                    self,
                )
                return

        for rect, lane, start, end in self._segment_rects:
            if rect.contains(point):
                bar = lane.bar.title() if lane.bar != "any" else "Any bar"
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{lane.label}\nActive {start:g}s–{end:g}s • {lane.duration_seconds:g}s duration • {bar}",
                    self,
                )
                return
        QToolTip.hideText()


class RotationTimelineWidget(QWidget):
    """Horizontally scrollable visual view of a canonical rotation projection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.canvas = _RotationTimelineCanvas()
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)

        self.setMinimumHeight(225)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_projection(self, projection: RotationTimelineProjection | None) -> None:
        self.canvas.set_projection(projection)

    def clear_projection(self) -> None:
        self.canvas.set_projection(None)


__all__ = ["RotationTimelineWidget"]
