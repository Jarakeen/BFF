from __future__ import annotations

from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path


THEME_DIR = ("assets", "themes", "bff", "grimoire")


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
    asset_dir = get_resource_path(*THEME_DIR, "assets").as_posix()
    return qss.replace("@ASSET_PATH@", asset_dir) + "\n" + UX_OVERRIDES


def apply_grimoire_theme(app: QApplication) -> bool:
    """Apply the Grimoire theme globally. Returns False if its QSS is unavailable."""
    qss = load_grimoire_stylesheet()
    if not qss:
        return False
    app.setStyle("Fusion")
    app.setStyleSheet(qss)
    return True
