from __future__ import annotations

"""Install the searchable Help center without duplicating MainWindow plumbing."""

from ui.components.foundry_sidebar import CORE_NAV_SECTIONS
from ui.help_page import HelpPage


_INSTALLED = False


def _ensure_help_navigation() -> None:
    if any(
        isinstance(item, tuple) and len(item) >= 2 and item[1] == "help"
        for item in CORE_NAV_SECTIONS
    ):
        return

    settings_index = next(
        (
            index
            for index, item in enumerate(CORE_NAV_SECTIONS)
            if isinstance(item, tuple) and len(item) >= 2 and item[1] == "settings"
        ),
        len(CORE_NAV_SECTIONS),
    )
    CORE_NAV_SECTIONS.insert(settings_index, ("Help & Guide", "help"))


def install() -> None:
    """Add Help navigation and a HelpPage to MainWindow before it is constructed."""
    global _INSTALLED
    if _INSTALLED:
        return

    _ensure_help_navigation()

    from ui.main_window import MainWindow

    original_build_ui = MainWindow.build_ui

    def build_ui_with_help(self) -> None:
        original_build_ui(self)
        if "help" in self.pages:
            return
        page = HelpPage()
        container = self.wrap_page(page)
        self.pages["help"] = page
        self.page_containers["help"] = container
        self.stack.addWidget(container)

    MainWindow.build_ui = build_ui_with_help
    _INSTALLED = True
