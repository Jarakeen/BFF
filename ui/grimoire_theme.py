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
/* ============================================================
   BFF UX theme-depth pass
   Dense book panels, visible leather, coherent parchment,
   compact operational controls, and recessed navigation.
   ============================================================ */

QWidget {
    font-family: "Montserrat", "Segoe UI";
    font-size: 12.5px;
}

QMainWindow, QDialog { background-color: #061315; }

/* ---------- Page hierarchy ---------- */
QWidget[foundryHeader="true"] {
    background: transparent;
    border-bottom: 1px solid #342C20;
}
QLabel[pageTitle="true"] {
    color: #D2B071;
    font-family: "Cinzel";
    font-size: 17px;
    font-weight: 700;
}
QLabel[pageSubtitle="true"] {
    color: #A7AAA2;
    font-family: "Cormorant Garamond", "Georgia";
    font-size: 12px;
    font-style: italic;
}
QLabel[departmentLabel="true"] {
    color: #8F948E;
    font-size: 10px;
}

/* ---------- Leather book panels ---------- */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"],
QWidget[bookPanel="true"] {
    background-color: #0B2022;
    background-image: url("@ASSET_PATH@/leather_teal.png");
    border-left: 1px solid #765D39;
    border-top: 1px solid #765D39;
    border-right: 1px solid #3B3023;
    border-bottom: 1px solid #33291E;
    border-radius: 3px;
}
QWidget[cardHeader="true"] {
    background-color: rgba(5, 15, 16, 145);
    border: none;
    border-bottom: 1px solid #5A472E;
    min-height: 28px;
    max-height: 34px;
}
QWidget[cardBody="true"] {
    background: transparent;
    border: none;
}
QLabel[cardTitle="true"] {
    color: #C9A965;
    font-family: "Cormorant Garamond", "Georgia";
    font-size: 13px;
    font-weight: 700;
}
QLabel[cardIcon="true"] { color: #B99255; }
QLabel[cardBadge="true"] {
    background-color: rgba(10, 27, 28, 180);
    color: #A7AAA2;
    border: 1px solid #59482F;
    border-radius: 7px;
    padding: 0px 6px;
    font-size: 9px;
}

/* ---------- Parchment is one continuous material ---------- */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #CBBB97;
    background-image: url("@ASSET_PATH@/parchment.png");
    color: #241D16;
    border-left: 1px solid #8A7048;
    border-top: 1px solid #8A7048;
    border-right: 1px solid #57462F;
    border-bottom: 1px solid #4E3E2B;
    border-radius: 3px;
}
QFrame[parchment="true"] QWidget[cardHeader="true"],
QFrame[parchment="true"] QWidget[cardBody="true"],
QFrame[foundryNoteCard="true"] QWidget[cardHeader="true"],
QFrame[foundryNoteCard="true"] QWidget[cardBody="true"] {
    background: transparent;
    border: none;
}
QFrame[parchment="true"] QWidget[cardHeader="true"],
QFrame[foundryNoteCard="true"] QWidget[cardHeader="true"] {
    border-bottom: 1px solid rgba(92, 68, 38, 145);
}
QFrame[parchment="true"] QLabel,
QWidget[parchment="true"] QLabel,
QFrame[foundryNoteCard="true"] QLabel,
QWidget[foundryNoteCard="true"] QLabel {
    background: transparent;
    color: #241D16;
    font-family: "Cormorant Garamond", "Georgia";
}
QFrame[parchment="true"] QLabel[cardTitle="true"],
QFrame[foundryNoteCard="true"] QLabel[cardTitle="true"] {
    color: #5A3D20;
}
QFrame[parchment="true"] QPlainTextEdit,
QFrame[parchment="true"] QTextEdit,
QFrame[foundryNoteCard="true"] QPlainTextEdit,
QFrame[foundryNoteCard="true"] QTextEdit {
    background: transparent;
    color: #241D16;
    border: none;
    font-family: "Cormorant Garamond", "Georgia";
}

/* ---------- Compact controls ---------- */
QPushButton {
    background-color: #0C2021;
    color: #DED5C5;
    border-left: 1px solid #806541;
    border-top: 1px solid #806541;
    border-right: 1px solid #453725;
    border-bottom: 1px solid #3B2F21;
    border-radius: 2px;
    padding: 3px 9px;
    min-height: 20px;
    max-height: 28px;
    font-family: "Montserrat", "Segoe UI";
    font-size: 10px;
}
QPushButton:hover {
    background-color: #143335;
    border-left-color: #A1844F;
    border-top-color: #A1844F;
}
QPushButton:pressed {
    background-color: #081819;
    border-left-color: #3B2F21;
    border-top-color: #3B2F21;
    border-right-color: #806541;
    border-bottom-color: #806541;
    padding-top: 4px;
    padding-bottom: 2px;
}
QPushButton[primary="true"], QPushButton[variant="primary"] {
    background-color: #143A3C;
    color: #F0E6D4;
    border-left-color: #9A794A;
    border-top-color: #9A794A;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3D2220;
    color: #E4CDC0;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {
    background-color: #09191A;
    color: #DDD5C6;
    border-left: 1px solid #3A3023;
    border-top: 1px solid #342B20;
    border-right: 1px solid #655239;
    border-bottom: 1px solid #655239;
    border-radius: 2px;
    padding: 3px 6px;
    min-height: 20px;
    max-height: 27px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #967747;
    background-color: #0D2223;
}

QCheckBox, QRadioButton { spacing: 5px; }
QCheckBox::indicator, QRadioButton::indicator { width: 13px; height: 13px; }

/* ---------- Tables become part of the card ---------- */
QTableWidget, QTableView {
    background-color: rgba(5, 16, 17, 105);
    alternate-background-color: rgba(18, 42, 43, 120);
    gridline-color: #302A21;
    border: 1px solid #493B29;
    padding: 0;
}
QFrame[tableCard="true"] QTableWidget,
QFrame[tableCard="true"] QTableView {
    border: none;
}
QHeaderView::section {
    background-color: rgba(10, 28, 29, 210);
    color: #C4A464;
    border: none;
    border-right: 1px solid #3D3427;
    border-bottom: 1px solid #57462F;
    padding: 4px 6px;
    font-family: "Cormorant Garamond", "Georgia";
    font-size: 11px;
    font-weight: 700;
    min-height: 22px;
}
QAbstractItemView::item { padding: 3px 5px; }

/* ---------- Tabs ---------- */
QTabWidget::pane { border: 1px solid #50412D; background-color: #071719; }
QTabBar::tab {
    background-color: #08191A;
    color: #B5B2A9;
    border: 1px solid #403628;
    padding: 4px 10px;
    min-height: 20px;
    font-size: 10px;
}
QTabBar::tab:selected {
    background-color: #123335;
    color: #D4B875;
    border-color: #806743;
}

/* ---------- Sidebar: engraved index rather than giant buttons ---------- */
QWidget[foundrySidebar="true"] {
    background-color: #051315;
    border-right: 1px solid #5E4A2E;
}
QWidget[foundrySidebar="true"] QScrollArea,
QWidget[foundrySidebar="true"] QScrollArea > QWidget > QWidget {
    background: transparent;
}
QLabel[sidebarLogo="true"] {
    color: #D0AE69;
    font-family: "Cinzel";
    font-size: 16px;
    font-weight: 700;
}
QLabel[sidebarOffice="true"] {
    color: #A88750;
    font-family: "Cormorant Garamond", "Georgia";
    font-size: 11px;
    letter-spacing: 1px;
}
QLabel[sidebarHeading="true"] {
    color: #B7955B;
    font-family: "Montserrat", "Segoe UI";
    font-size: 9px;
    font-weight: 700;
}
QLabel[sidebarMeta="true"], QLabel[sidebarFooter="true"] {
    color: #898F8A;
    font-size: 9px;
}
QPushButton[nav="true"] {
    background-color: transparent;
    color: #C5C0B5;
    border: 1px solid transparent;
    border-radius: 2px;
    text-align: left;
    padding: 3px 7px;
    min-height: 20px;
    max-height: 30px;
}
QPushButton[nav="true"]:hover {
    background-color: rgba(14, 43, 45, 150);
    border-color: #44392A;
}
QPushButton[nav="true"]:checked {
    background-color: #103234;
    color: #D6B66F;
    border-left: 2px solid #9B7A48;
    border-top: 1px solid #59472F;
    border-right: 1px solid #33291F;
    border-bottom: 1px solid #33291F;
}

/* ---------- Existing special UX selectors ---------- */
QFrame[settingsRail="true"] {
    background-color: #071517;
    border: 1px solid #4E402C;
    border-radius: 3px;
}
QPushButton[settingsNav="true"] {
    background-color: transparent;
    border: 1px solid transparent;
    color: #CFC6B5;
    text-align: left;
    padding: 5px 8px;
}
QPushButton[settingsNav="true"]:hover { background-color: #0E2628; border-color: #4D412F; }
QPushButton[settingsNav="true"]:checked { background-color: #3D3020; color: #F0D59A; border-color: #876C41; }

QLabel[integrationState="true"] { color: #9CCB82; }
QLabel[heroTitle="true"] { color: #D0AD69; font-family: "Cormorant Garamond", "Georgia"; font-size: 19px; font-weight: 700; }
QLabel[heroSubtitle="true"] { color: #C0AA7B; font-family: "Cormorant Garamond", "Georgia"; font-size: 12px; }
QLabel[bossArtworkPlaceholder="true"], QLabel[positioningMap="true"] {
    background-color: rgba(6, 20, 21, 145);
    border: 1px solid #5E4A2E;
    color: #817767;
    font-family: "Cormorant Garamond", "Georgia";
}
QLabel[positioningMap="true"] { font-size: 13px; }
QLabel[timerValue="true"] { color: #D8C39C; font-family: "Cinzel"; font-size: 31px; padding: 5px; }
QLabel[warningText="true"] { color: #D39B50; }
QLabel[successText="true"] { color: #8FC0A5; }
QLabel[criticalText="true"] { color: #C97D66; }
"""


def load_grimoire_stylesheet() -> str:
    """Load base QSS, add UX overrides, then resolve all bundled asset URLs."""
    qss_path = get_resource_path(*THEME_DIR, "grimoire.qss")
    if not qss_path.exists():
        return ""

    qss = qss_path.read_text(encoding="utf-8") + "\n" + UX_OVERRIDES
    asset_dir = get_resource_path(*THEME_DIR, "assets").as_posix()
    return qss.replace("@ASSET_PATH@", asset_dir)


def apply_grimoire_theme(app: QApplication) -> bool:
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
    def __init__(self, parent=None, opacity=0.22):
        super().__init__(parent)
        self.opacity = opacity

    def eventFilter(self, obj, event):
        if isinstance(obj, QPushButton) and event.type() == QEvent.Type.Paint:
            return False
        return super().eventFilter(obj, event)


class StudButton(QPushButton):
    """Drop-in QPushButton with subtle brass edge studs."""

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