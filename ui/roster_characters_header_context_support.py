from __future__ import annotations

"""Hide assignment-oriented header filters while the Characters tab is active.

The shared Roster header owns View By / Filter By Role / Show controls that make
sense for assignment/roster views, but they do not filter the canonical
Player -> Character -> Build tree. This support only changes visibility; it does
not replace or duplicate any roster state.
"""

_INSTALLED = False


def _is_characters_tab(page, index: int) -> bool:
    tabs = getattr(page, "tabs", None)
    if tabs is None or index < 0 or index >= tabs.count():
        return False
    return tabs.tabText(index).strip().casefold() == "characters"


def _context_container(widget):
    return widget.parentWidget() if widget is not None else None


def _sync_header_context(page, index: int | None = None) -> None:
    tabs = getattr(page, "tabs", None)
    if tabs is None:
        return
    current = tabs.currentIndex() if index is None else index
    hide = _is_characters_tab(page, current)

    for name in ("view_combo", "role_combo", "show_combo"):
        container = _context_container(getattr(page, name, None))
        if container is not None:
            container.setVisible(not hide)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_ui = RosterPage._build_ui

    def build_ui_with_character_header_context(self) -> None:
        original_build_ui(self)
        self.tabs.currentChanged.connect(
            lambda index: _sync_header_context(self, index)
        )
        _sync_header_context(self)

    RosterPage._build_ui = build_ui_with_character_header_context
    _INSTALLED = True
