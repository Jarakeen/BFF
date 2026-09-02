from __future__ import annotations

"""Give the Builds workspace exactly one vertical scroll owner.

FoundryPage normally wraps its workspace in a QScrollArea. The permanent Builds
workspace tabs include controls that already own their scrolling (the Edit tab,
Character Progression panes, and the Scribed Skills list). Allowing the outer
FoundryPage scroll area to remain vertically scrollable creates nested vertical
scrollbars, competing wheel handling, and expensive relayouts during tab
changes.

This compatibility layer disables only the outer Builds workspace vertical
scrollbar. Individual tabs remain responsible for their own scrolling.
"""

from PySide6.QtCore import Qt

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui

    def build_ui_with_single_scroll_owner(self) -> None:
        original_build_ui(self)
        self.workspace_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.workspace_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    BuildsPage._build_ui = build_ui_with_single_scroll_owner
    _INSTALLED = True
