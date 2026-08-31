from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

from engine.config import get_resource_path


def _fallback_pixmap() -> QPixmap:
    """Return a calm static fallback if the fantasy splash asset is absent."""
    pixmap = QPixmap(960, 540)
    pixmap.fill(QColor("#0C171B"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(QColor("#C8A46A"))
    painter.drawRect(18, 18, 923, 503)

    title_font = QFont("Cinzel")
    title_font.setPointSize(28)
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.drawText(
        pixmap.rect().adjusted(50, 130, -50, -250),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "BLACK FEATHER FOUNDRY",
    )

    subtitle_font = QFont("Cormorant Garamond")
    subtitle_font.setPointSize(18)
    painter.setFont(subtitle_font)
    painter.drawText(
        pixmap.rect().adjusted(50, 220, -50, -170),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "FIELD OFFICE",
    )

    body_font = QFont("Cormorant Garamond")
    body_font.setPointSize(13)
    painter.setFont(body_font)
    painter.drawText(
        pixmap.rect().adjusted(50, 330, -50, -90),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "Cataloguing glory. Survival remains under review.",
    )

    painter.end()
    return pixmap


def create_splash() -> QSplashScreen:
    """Create the static, non-animated Foundry startup splash."""
    splash_path = get_resource_path(
        "assets",
        "themes",
        "bff",
        "grimoire",
        "assets",
        "fantasy_splash.png",
    )

    pixmap = QPixmap(str(splash_path)) if splash_path.exists() else QPixmap()
    if pixmap.isNull():
        pixmap = _fallback_pixmap()

    # Keep startup visually calm. One static image, no fades, cycling text,
    # progress animation, or other transient effects.
    if pixmap.width() > 1400:
        pixmap = pixmap.scaledToWidth(
            1400,
            Qt.TransformationMode.SmoothTransformation,
        )

    return QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
