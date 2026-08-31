from __future__ import annotations
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtGui import QColor, QPainter
from engine.config import get_resource_path

THEME_DIR = ("assets", "themes", "bff", "grimoire")

COLORS = {
    "base": "#061315",
    "shadow": "#081719",
    "surface_1": "#0B2022",
    "surface_2": "#10292B",
    "surface_hover": "#153436",
    "teal": "#164447",
    "teal_bright": "#1B5154",
    "gold": "#A1844F",
    "gold_soft": "#C6A361",
    "parchment": "#CBBB97",
    "ink": "#241D16",
    "text": "#E2DAC9",
    "muted": "#9DA5A0",
    "danger": "#402322",
}


UX_OVERRIDES = r"""
/* UX branch: Settings / Encounters / Mechanics */
QFrame[settingsRail="true"] {
    background-color: #071517;
    border: 1px solid #4E402C;
    border-radius: 4px;
}
QPushButton[settingsNav="true"] {
    background-color: transparent;
    border: 1px solid transparent;
    color: #CFC6B5;
    text-align: left;
    padding: 8px 10px;
}
QPushButton[settingsNav="true"]:hover {
    background-color: #0E2628;
    border-color: #4D412F;
}
QPushButton[settingsNav="true"]:checked {
    background-color: #4A3821;
    color: #F0D59A;
    border-color: #876C41;
}
QLabel[integrationState="true"] {
    color: #9CCB82;
}
QLabel[heroTitle="true"] {
    color: #D0AD69;
    font-family: "Georgia";
    font-size: 22px;
    font-weight: 600;
}
QLabel[heroSubtitle="true"] {
    color: #C0AA7B;
    font-family: "Georgia";
    font-size: 14px;
}
QLabel[bossArtworkPlaceholder="true"],
QLabel[positioningMap="true"] {
    background-color: #0A1718;
    border: 1px solid #5E4A2E;
    color: #7F7767;
    font-family: "Georgia";
}
QLabel[positioningMap="true"] {
    font-size: 14px;
    line-height: 1.35;
}
QLabel[timerValue="true"] {
    color: #D8C39C;
    font-family: "Georgia";
    font-size: 38px;
    padding: 8px;
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel {
    background: transparent;
    color: #241D16;
    font-family: "Georgia";
}
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit {
    background: transparent;
    color: #241D16;
    border: none;
    font-family: "Georgia";
}
"""




def load_grimoire_stylesheet() -> str:
    """Load the BFF Grimoire QSS and resolve bundled asset URLs."""
    qss_path = get_resource_path(*THEME_DIR, "grimoire.qss")

    if not qss_path.exists():
        return ""

    qss = qss_path.read_text(encoding="utf-8")
    asset_dir = get_resource_path(
        *THEME_DIR,
        "assets",
    ).as_posix()

    qss = qss.replace(
        "@ASSET_PATH@",
        asset_dir,
    )

    return qss + "\n" + UX_OVERRIDES

def apply_grimoire_theme(app: QApplication) -> bool:
    """Apply the Grimoire theme globally. Returns False if its QSS is unavailable."""
    qss = load_grimoire_stylesheet()
    if not qss:
        return False
    app.setStyle("Fusion")
    app.setStyleSheet(qss)
    return True


def set_role(widget, role: str) -> None:
    widget.setProperty("role", role)
    _repolish(widget)

def make_book_panel(widget, raised: bool = False) -> None:
    widget.setProperty("bookPanel", True)
    widget.setProperty("raised", raised)
    _repolish(widget)

def make_parchment(widget, enabled: bool = True) -> None:
    """
    Give a widget a parchment surface.
    Recommended for Observation, Archive Preview, and document-like Timeline views.
    """
    widget.setProperty("parchment", enabled)
    _repolish(widget)

def set_button_variant(button: QPushButton, variant: str = "primary") -> None:
    button.setProperty("variant", variant)
    _repolish(button)

def _repolish(widget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()

class SubtleStudFilter(QObject):
    """
    Optional tiny burnished-gold 'book binding' dots on button edges.

    It deliberately paints only two 1.0px dots, with very low opacity.
    This is meant to read as depth/hardware, not decorative luggage.
    """
    def __init__(self, parent=None, opacity=0.22):
        super().__init__(parent)
        self.opacity = opacity

    def eventFilter(self, obj, event):
        if isinstance(obj, QPushButton) and event.type() == QEvent.Type.Paint:
            # Let Qt finish the normal paint first, then overlay via a zero-delay update
            # is unreliable; instead this filter is intended for use with StudButton below.
            return False
        return super().eventFilter(obj, event)

class StudButton(QPushButton):
    """Drop-in QPushButton with very subtle brass edge studs."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = QColor("#A1844F")
        c.setAlphaF(0.22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        r = 1.0
        y = self.height() / 2
        painter.drawEllipse(5.0 - r, y - r, r * 2, r * 2)
        painter.drawEllipse(self.width() - 5.0 - r, y - r, r * 2, r * 2)
        painter.end()
