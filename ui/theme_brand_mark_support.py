from __future__ import annotations

"""Keep the top-left Foundry brand and release navigation synchronized."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from engine.config import get_resource_path
from services.release_feature_policy import release_mode, route_allowed

_INSTALLED = False
_LOGO = ("assets", "logos", "BFF_logo.png")


def _filter_release_sections(sections: list) -> list:
    """Remove non-release routes while preserving category structure and ordering."""
    if not release_mode():
        return sections

    filtered: list = []
    for section in sections:
        if isinstance(section, tuple):
            if len(section) >= 2 and route_allowed(section[1]):
                filtered.append(section)
            continue

        if not isinstance(section, dict):
            continue

        page = section.get("page")
        if page and not route_allowed(page):
            continue

        children = [
            child
            for child in section.get("children", ())
            if len(child) >= 2 and route_allowed(child[1])
        ]
        clone = dict(section)
        clone["children"] = children

        # A category with neither a page nor release-approved children has no
        # purpose in the packaged navigation and should disappear entirely.
        if not clone.get("page") and not children:
            continue
        filtered.append(clone)

    return filtered


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import foundry_sidebar as sidebar_module
    from ui.components.foundry_sidebar import FoundrySidebar
    from ui.theme.theme_manager import ThemeManager

    original_apply = ThemeManager.apply
    original_build_ui = FoundrySidebar.build_ui
    original_nav_sections = sidebar_module.nav_sections

    def release_aware_nav_sections(include_broadcast: bool) -> list:
        return _filter_release_sections(original_nav_sections(include_broadcast))

    sidebar_module.nav_sections = release_aware_nav_sections

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
