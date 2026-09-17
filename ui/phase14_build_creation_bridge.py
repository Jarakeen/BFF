from __future__ import annotations

"""Route the Phase 14 command-center New Build action to the existing creator.

The Character Creation Easy Mode feature remains the sole creation authority. This
bridge only moves its entry point into the Phase 14 top row and hides the older
centered duplicate button; it does not create a second build-creation path.
"""

_INSTALLED = False
_ORIGINAL_BUILD_UI = None


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    _ORIGINAL_BUILD_UI = BuildsPage._build_ui

    def build_ui_with_phase14_creation(self):
        _ORIGINAL_BUILD_UI(self)
        button = getattr(self, "phase14_create_build_button", None)
        panel = getattr(self, "new_build_panel", None)
        if button is not None and panel is not None:
            button.setEnabled(True)
            button.setToolTip("Create a new character/build using the existing review-first FoundryDock creation workflow.")
            button.clicked.connect(panel.open_for_creation)

        # The Phase 14 top row now owns the visible creation entry point. Keep the
        # underlying panel and workflow, but remove the older duplicate centered button.
        old_host = getattr(self, "new_build_action_host", None)
        if old_host is not None:
            old_host.hide()
        old_button = getattr(self, "create_character_button", None)
        if old_button is not None:
            old_button.hide()

    BuildsPage._build_ui = build_ui_with_phase14_creation
    _INSTALLED = True


__all__ = ["install"]
