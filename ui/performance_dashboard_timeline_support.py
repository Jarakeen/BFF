from __future__ import annotations

"""Draw selected support-effect windows directly beneath the output graph."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.theme.colors import Colors

_INSTALLED = False


class _EffectTimelineWidget(QWidget):
    LABEL_WIDTH = 150
    ROW_HEIGHT = 24

    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def refresh(self) -> None:
        names = list(getattr(self.page, "_graph_effect_names", ()))
        rows = max(1, len(names))
        self.setFixedHeight(18 + rows * self.ROW_HEIGHT)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        snapshot = getattr(self.page, "_last_snapshot", None)
        names = list(getattr(self.page, "_graph_effect_names", ()))
        if snapshot is None or not names:
            painter.setPen(QColor(Colors.TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select effects and load a fight to show exact aura windows.")
            return

        duration = float(getattr(snapshot, "FightDurationSeconds", 0.0) or 0.0)
        windows = list(getattr(snapshot, "EffectWindows", ()) or ())
        error = str(getattr(snapshot, "EffectTimelineError", "") or "").strip()
        if duration <= 0:
            painter.setPen(QColor(Colors.TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Fight duration unavailable for effect timeline.")
            return

        left = float(self.LABEL_WIDTH)
        right = float(max(self.LABEL_WIDTH + 20, self.width() - 12))
        track_width = max(1.0, right - left)

        painter.setPen(QPen(QColor(Colors.TEXT_MUTED), 1))
        painter.drawText(QRectF(left, 0, track_width, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "0:00")
        end_minutes = int(duration) // 60
        end_seconds = int(duration) % 60
        painter.drawText(QRectF(left, 0, track_width, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{end_minutes}:{end_seconds:02d}")

        selected_keys = {name.casefold(): name for name in names}
        rows_by_name: dict[str, list] = {key: [] for key in selected_keys}
        for window in windows:
            key = str(getattr(window, "Name", "") or "").strip().casefold()
            if key in rows_by_name:
                rows_by_name[key].append(window)

        for row_index, name in enumerate(names):
            y = 18 + row_index * self.ROW_HEIGHT
            painter.setPen(QColor(Colors.TEXT))
            painter.drawText(QRectF(0, y, self.LABEL_WIDTH - 8, self.ROW_HEIGHT), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)

            track = QRectF(left, y + 6, track_width, 12)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(Colors.SURFACE_LIGHT))
            painter.drawRoundedRect(track, 4, 4)

            effect_windows = rows_by_name.get(name.casefold(), [])
            if not effect_windows:
                painter.setPen(QColor(Colors.TEXT_MUTED))
                painter.drawText(track, Qt.AlignmentFlag.AlignCenter, "no exact events")
                continue

            for window in effect_windows:
                start = max(0.0, min(duration, float(getattr(window, "StartSeconds", 0.0) or 0.0)))
                end = max(start, min(duration, float(getattr(window, "EndSeconds", start) or start)))
                if end <= start:
                    continue
                x = left + (start / duration) * track_width
                width = max(2.0, ((end - start) / duration) * track_width)
                segment = QRectF(x, y + 6, width, 12)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(Colors.ACCENT_LIGHT))
                painter.drawRoundedRect(segment, 4, 4)

        if error and not windows:
            painter.setPen(QColor(Colors.TEXT_MUTED))
            painter.drawText(
                QRectF(left, self.height() - 18, track_width, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "Exact effect events unavailable; aggregate uptime above is still valid.",
            )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    original_build_ui = PerformanceDashboard.build_ui
    original_show_snapshot = PerformanceDashboard.show_snapshot

    def build_ui_with_effect_timeline(self):
        original_build_ui(self)
        card = getattr(self, "output_card", None)
        if card is None:
            return

        label = QLabel("Effect timeline")
        label.setProperty("sidebarHeading", True)
        label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
        card.addWidget(label)

        self.effect_timeline_widget = _EffectTimelineWidget(self, card)
        card.addWidget(self.effect_timeline_widget)

        for checkbox in getattr(self, "graph_effect_checkboxes", {}).values():
            checkbox.toggled.connect(self.effect_timeline_widget.refresh)
        self.effect_timeline_widget.refresh()

    def show_snapshot_with_effect_timeline(self, snapshot):
        original_show_snapshot(self, snapshot)
        widget = getattr(self, "effect_timeline_widget", None)
        if widget is not None:
            widget.refresh()

    PerformanceDashboard.build_ui = build_ui_with_effect_timeline
    PerformanceDashboard.show_snapshot = show_snapshot_with_effect_timeline
    _INSTALLED = True
