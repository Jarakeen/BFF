from __future__ import annotations

"""Install the searchable Help center without duplicating MainWindow plumbing."""

from PySide6.QtWidgets import QPushButton

from ui.help_page import HelpPage


_INSTALLED = False

_CONTEXT_TOPICS = {
    "console:2": "builds",
    "roster_page": "roster",
    "comp_builder": "comp_builder",
    "console:6": "optimization",
    "console:7": "coverage",
    "console:4": "mechanics",
    "console:8": "reference_data",
    "timers": "timers",
    "settings": "settings",
}


def _open_topic(window, topic_key: str) -> None:
    window.show_page("help")
    page = window.pages.get("help")
    if page is not None:
        page.show_topic(topic_key)


def _add_context_help_buttons(window) -> None:
    for page_key, topic_key in _CONTEXT_TOPICS.items():
        page = window.pages.get(page_key)
        header = getattr(page, "header", None)
        if page is None or header is None:
            continue
        button = QPushButton("? Help")
        button.setToolTip("Open help for this page.")
        button.setProperty("helpButton", True)
        button.clicked.connect(
            lambda checked=False, key=topic_key: _open_topic(window, key)
        )
        header.add_context_widget(button)


def install() -> None:
    """Add HelpPage and contextual page help before MainWindow construction."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.main_window import MainWindow

    original_build_ui = MainWindow.build_ui

    def build_ui_with_help(self) -> None:
        original_build_ui(self)
        if "help" not in self.pages:
            page = HelpPage()
            container = self.wrap_page(page)
            self.pages["help"] = page
            self.page_containers["help"] = container
            self.stack.addWidget(container)
        _add_context_help_buttons(self)

    MainWindow.build_ui = build_ui_with_help
    _INSTALLED = True
