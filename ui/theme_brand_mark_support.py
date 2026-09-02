from __future__ import annotations

"""Keep the top-left Foundry/Rylo brand mark synchronized with visual theme."""

from PySide6.QtWidgets import QApplication

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme.theme_manager import ThemeManager

    original_apply = ThemeManager.apply

    def apply_with_brand_mark(self, app: QApplication) -> None:
        original_apply(self, app)
        try:
            from ui.components.foundry_sidebar import FoundrySidebar
            for top in app.topLevelWidgets():
                for sidebar in top.findChildren(FoundrySidebar):
                    sidebar.refresh_brand_mark()
        except (ImportError, RuntimeError):
            # Startup applies the theme before MainWindow exists; the sidebar
            # chooses the correct mark itself when it is later constructed.
            pass

    ThemeManager.apply = apply_with_brand_mark
    _INSTALLED = True
