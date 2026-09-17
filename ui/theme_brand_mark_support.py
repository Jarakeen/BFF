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
    original_build_ui = FoundrySidebar.build_ui

    def refresh_brand_mark_sized(self) -> None:
        if not hasattr(self, "brand_mark"):
            return

        self.setMinimumWidth(248)
        self.setMaximumWidth(278)
        self.brand_mark.setFixedSize(228, 152)
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        path = get_resource_path(*_LOGO)
        pixmap = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
        self.brand_mark.clear()
        if not pixmap.isNull():
            self.brand_mark.setPixmap(
                pixmap.scaled(
                    224,
                    148,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.brand_mark.setText("BFF")

        # The approved image already contains BFF + "we got this". Remove the
        # legacy text lockup entirely after construction so it cannot overlap or
        # reserve stray layout width beside the image.
        brand_parent = self.brand_mark.parentWidget()
        if brand_parent is not None:
            layout = brand_parent.layout()
            if layout is not None:
                layout.setSpacing(0)
                layout.setAlignment(self.brand_mark, Qt.AlignmentFlag.AlignCenter)
            for label in brand_parent.findChildren(QLabel):
                if label is self.brand_mark:
                    continue
                if bool(label.property("sidebarLogo")) or bool(label.property("sidebarOffice")):
                    label.hide()
                    label.setParent(None)
                    label.deleteLater()

    FoundrySidebar.refresh_brand_mark = refresh_brand_mark_sized

    def build_ui_with_brand(self) -> None:
        # FoundrySidebar creates its legacy text after its first brand refresh.
        # Refresh once more after construction so only the approved logo remains.
        original_build_ui(self)
        self.refresh_brand_mark()

    FoundrySidebar.build_ui = build_ui_with_brand

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
