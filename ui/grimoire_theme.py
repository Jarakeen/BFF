from __future__ import annotations

from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path


THEME_DIR = ("assets", "themes", "bff", "grimoire")


def load_grimoire_stylesheet() -> str:
    """Load the BFF Grimoire QSS and resolve bundled asset URLs."""
    qss_path = get_resource_path(*THEME_DIR, "grimoire.qss")
    if not qss_path.exists():
        return ""

    qss = qss_path.read_text(encoding="utf-8")
    asset_dir = get_resource_path(*THEME_DIR, "assets").as_posix()
    return qss.replace("@ASSET_PATH@", asset_dir)


def apply_grimoire_theme(app: QApplication) -> bool:
    """Apply the Grimoire theme globally. Returns False if its QSS is unavailable."""
    qss = load_grimoire_stylesheet()
    if not qss:
        return False
    app.setStyle("Fusion")
    app.setStyleSheet(qss)
    return True
