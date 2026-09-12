from __future__ import annotations

"""Decorative, explicitly unverified imagery for empty reference-art slots."""

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO


class FieldOfficeEmptyArtwork(QLabel):
    """Shows field art only while no real, user-provided pixmap is installed."""

    def __init__(self, filename: str, text: str, parent=None):
        super().__init__(text, parent)
        self._field_art = QPixmap(str(get_resource_path("assets", "field_office_placeholders", filename)))
        self._rylo_art = QPixmap(str(get_resource_path("assets", "field_office_placeholders", f"rylo_{filename}")))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setToolTip(text)
        self.setProperty("bossArtworkPlaceholder", True)

    def paintEvent(self, event):  # noqa: N802
        actual = self.pixmap()
        if actual is not None and not actual.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rylo = QApplication.instance() is not None and QApplication.instance().property("visualTheme") == VISUAL_THEME_RYLO
        art = self._rylo_art if rylo and not self._rylo_art.isNull() else self._field_art
        painter.fillRect(self.rect(), QColor("#30363B" if rylo else "#D7C6A5"))
        if not art.isNull():
            image = art.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            left = (image.width() - self.width()) // 2
            top = (image.height() - self.height()) // 2
            painter.drawPixmap(self.rect(), image, QRect(left, top, self.width(), self.height()))

        caption = QRect(10, max(10, self.height() - 78), max(80, self.width() - 20), 68)
        painter.fillRect(caption, QColor(225, 228, 225, 238) if rylo else QColor(239, 226, 199, 238))
        painter.setPen(QPen(QColor("#596368" if rylo else "#7C6035"), 1))
        painter.drawRect(caption.adjusted(0, 0, -1, -1))
        lines = [part.strip() for part in self.text().splitlines() if part.strip()]
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor("#162529"))
        if lines:
            headline = painter.fontMetrics().elidedText(lines[0], Qt.TextElideMode.ElideRight, caption.width() - 22)
            painter.drawText(caption.adjusted(10, 7, -10, -37), Qt.AlignmentFlag.AlignCenter, headline)
        if len(lines) > 1:
            font.setBold(False)
            font.setPointSize(8)
            painter.setFont(font)
            detail = painter.fontMetrics().elidedText(" ".join(lines[1:]), Qt.TextElideMode.ElideRight, caption.width() - 22)
            painter.drawText(caption.adjusted(10, 35, -10, -8), Qt.AlignmentFlag.AlignCenter, detail)
        painter.end()
