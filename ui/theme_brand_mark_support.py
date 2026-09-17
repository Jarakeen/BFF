from __future__ import annotations

"""Keep the top-left Foundry brand synchronized with the active visual theme."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from engine.config import get_resource_path

_INSTALLED = False
_LOGO = ("assets", "logos", "BFF_logo.png")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components.foundry_sidebar import FoundrySidebar
    from ui.theme.theme_manager import ThemeManager

    original_apply = ThemeManager.apply

    def refresh_brand_mark_sized(self) -> None:
        if not hasattr(self, "brand_mark"):
            return

        # The approved BFF logo already contains the title and "we got this"
        # subline, so the legacy text labels beside it are intentionally hidden.
        self.setMinimumWidth(248)
        self.setMaximumWidth(278)
        self.brand_mark.setFixedSize(222, 140)
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        path = get_resource_path(*_LOGO)
        pixmap = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
        self.brand_mark.clear()
        if not pixmap.isNull():
            self.brand_mark.setPixmap(
                pixmap.scaled(
                    218,
                    136,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.brand_mark.setText("BFF")

        brand_parent = self.brand_mark.parentWidget()
        if brand_parent is not None:
            for label in brand_parent.findChildren(QLabel):
                if label is self.brand_mark:
                    continue
                if bool(label.property("sidebarLogo")) or bool(label.property("sidebarOffice")):
                    label.hide()

    FoundrySidebar.refresh_brand_mark = refresh_brand_mark_sized

    def apply_with_brand_mark(self, app: QApplication) -> None:
        original_apply(self, app)
        try:
            for top in app.topLevelWidgets():
                for sidebar in top.findChildren(FoundrySidebar):
                    sidebar.refresh_brand_mark()
        except RuntimeError:
            # Startup applies the theme before MainWindow exists; the sidebar
            # chooses the approved logo itself when it is later constructed.
            pass

    ThemeManager.apply = apply_with_brand_mark
    _INSTALLED = True
