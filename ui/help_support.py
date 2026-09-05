from __future__ import annotations

"""Install the searchable Help center inside the Settings section rail."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QPushButton

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


def _settings_rail(settings_page):
    return next(
        (
            frame
            for frame in settings_page.findChildren(QFrame)
            if frame.property("settingsRail") is True
        ),
        None,
    )


def _install_settings_help(window) -> None:
    settings_page = window.pages.get("settings")
    if settings_page is None or hasattr(settings_page, "help_page"):
        return

    rail = _settings_rail(settings_page)
    rail_layout = rail.layout() if rail is not None else None
    if rail_layout is None:
        return

    help_page = HelpPage()
    help_index = settings_page.stack.addWidget(help_page)

    button = QPushButton("?   Help & Guide")
    button.setCheckable(True)
    button.setProperty("settingsNav", True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(
        lambda _checked=False, index=help_index: settings_page._show_section(index)
    )

    # Settings adds a stretch after its normal navigation buttons. Insert Help
    # immediately before that stretch so it appears with General, Appearance,
    # Advanced, About & Credits, etc., rather than in the global app sidebar.
    insert_at = max(0, rail_layout.count() - 1)
    rail_layout.insertWidget(insert_at, button)
    settings_page._section_buttons.append(button)
    settings_page.help_page = help_page
    settings_page.help_section_index = help_index


def _open_topic(window, topic_key: str) -> None:
    settings_page = window.pages.get("settings")
    if settings_page is None or not hasattr(settings_page, "help_page"):
        return
    window.show_page("settings")
    settings_page._show_section(settings_page.help_section_index)
    settings_page.help_page.show_topic(topic_key)


def _add_context_help_buttons(window) -> None:
    for page_key, topic_key in _CONTEXT_TOPICS.items():
        page = window.pages.get(page_key)
        header = getattr(page, "header", None)
        if page is None or header is None:
            continue
        button = QPushButton("? Help")
        button.setToolTip("Open help for this page in Settings.")
        button.setProperty("helpButton", True)
        button.clicked.connect(
            lambda checked=False, key=topic_key: _open_topic(window, key)
        )
        header.add_context_widget(button)


def install() -> None:
    """Embed Help in Settings and wire contextual page help before construction."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.main_window import MainWindow

    original_build_ui = MainWindow.build_ui

    def build_ui_with_help(self) -> None:
        original_build_ui(self)
        _install_settings_help(self)
        _add_context_help_buttons(self)

    MainWindow.build_ui = build_ui_with_help
    _INSTALLED = True
