from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSplashScreen

from engine.config import get_resource_path


_STARTUP_LINES = (
    "Consulting the index. It remains alphabetical.",
    "Gathering the records. Nothing has escaped yet.",
    "Opening the field office. Paperwork has survived.",
    "Checking the lantern. Bureaucracy proceeds.",
    "Assembling the expedition. Someone brought a clipboard.",
    "Reviewing the notes. Conclusions remain cautiously optimistic.",
)


def _font(family: str, size: int, *, bold: bool = False, italic: bool = False) -> QFont:
    font = QFont(family, size)
    font.setBold(bold)
    font.setItalic(italic)
    return font


def _draw_centered_text(
    painter: QPainter,
    text: str,
    y: int,
    height: int,
    font: QFont,
    color: QColor,
) -> None:
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(
        0,
        y,
        680,
        height,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        text,
    )


def _fantasy_splash_pixmap() -> QPixmap:
    """Return the optional fantasy splash artwork when it is installed locally."""
    for filename in ("fantasy_splash.png", "fantasy_splash.jpg", "fantasy_splash.jpeg"):
        path = get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets", filename
        )
        if not path.exists():
            continue

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            continue

        if pixmap.width() > 1400:
            pixmap = pixmap.scaledToWidth(
                1400,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pixmap

    return QPixmap()


def _fallback_pixmap() -> QPixmap:
    """Build the original static BFF splash if the fantasy artwork is absent."""
    width, height = 680, 400
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#0C171B"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setPen(QPen(QColor("#C8A46A"), 2))
    painter.drawRect(12, 12, width - 24, height - 24)
    painter.setPen(QPen(QColor("#2F7A80"), 1))
    painter.drawRect(20, 20, width - 40, height - 40)

    feather_path = get_resource_path(
        "assets", "themes", "bff", "grimoire", "assets", "feather_watermark.svg"
    )
    if feather_path.exists():
        feather = QPixmap(str(feather_path))
        if not feather.isNull():
            feather = feather.scaled(
                92,
                150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.setOpacity(0.48)
            painter.drawPixmap((width - feather.width()) // 2, 45, feather)
            painter.setOpacity(1.0)

    _draw_centered_text(
        painter,
        "BLACK FEATHER FOUNDRY",
        178,
        42,
        _font("Cinzel", 22, bold=True),
        QColor("#E5ECEB"),
    )
    _draw_centered_text(
        painter,
        "FIELD OFFICE",
        216,
        30,
        _font("Montserrat", 10, bold=True),
        QColor("#59AEB3"),
    )

    painter.setPen(QPen(QColor("#C8A46A"), 1))
    painter.drawLine(188, 263, 492, 263)

    startup_line = random.choice(_STARTUP_LINES)
    _draw_centered_text(
        painter,
        startup_line,
        278,
        48,
        _font("Cormorant Garamond", 13, italic=True),
        QColor("#BFC8C6"),
    )
    _draw_centered_text(
        painter,
        "Leave better records.",
        342,
        24,
        _font("Cormorant Garamond", 10),
        QColor("#C8A46A"),
    )

    painter.end()
    return pixmap


def create_startup_splash() -> QSplashScreen:
    """Create a completely static, motion-free startup screen.

    The fantasy artwork is preferred when present. The original BFF field-office
    plate remains as a safe fallback. Neither version animates, blinks, fades,
    cycles text, or displays a moving progress indicator.
    """
    pixmap = _fantasy_splash_pixmap()
    if pixmap.isNull():
        pixmap = _fallback_pixmap()

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.setAccessibleName("Black Feather Foundry startup screen")
    splash.setAccessibleDescription(
        "Static startup screen with no flashing or animated content."
    )
    return splash
