from __future__ import annotations

"""Keep the top-left Foundry/Rylo brand mark synchronized with visual theme."""

from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


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

        app = QApplication.instance()
        rylo = bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)
        if rylo:
            filename = "sidebar_scythe_rylo.svg"
            pix_w, pix_h = 48, 62
            box_w, box_h = 54, 68
        else:
            filename = "sidebar_feather_gold.svg"
            pix_w, pix_h = 32, 52
            box_w, box_h = 38, 56

        self.brand_mark.setFixedSize(box_w, box_h)
        pixmap = self._asset_pixmap(filename, pix_w, pix_h)
        self.brand_mark.clear()
        if not pixmap.isNull():
            self.brand_mark.setPixmap(pixmap)
        else:
            self.brand_mark.setText("✦")

    FoundrySidebar.refresh_brand_mark = refresh_brand_mark_sized

    def apply_with_brand_mark(self, app: QApplication) -> None:
        original_apply(self, app)
        try:
            for top in app.topLevelWidgets():
                for sidebar in top.findChildren(FoundrySidebar):
                    sidebar.refresh_brand_mark()
        except RuntimeError:
            # Startup applies the theme before MainWindow exists; the sidebar
            # chooses the correct mark itself when it is later constructed.
            pass

    ThemeManager.apply = apply_with_brand_mark
    _INSTALLED = True
