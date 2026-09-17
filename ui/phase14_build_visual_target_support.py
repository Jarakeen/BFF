from __future__ import annotations

"""Final Phase 14 Builds presentation polish.

The target mockup has one New Build action inside the library command row and a
persistent right-hand inspector. Older decorators may still alter splitter geometry
or restore legacy header chrome after the command center is created, so this module
applies the visual contract again at the actual themed BuildsPage boundary.

Presentation only. Canonical build/editor actions and user data remain untouched.
"""

from shiboken6 import isValid

_INSTALLED = False


def _valid(obj) -> bool:
    if obj is None:
        return False
    try:
        return bool(isValid(obj))
    except RuntimeError:
        return False


def apply_phase14_build_visual_target(page) -> None:
    """Apply the final Builds mockup geometry after every legacy wrapper has returned."""
    # Keep the old Easy Mode action alive as the canonical implementation, but remove
    # its duplicate header presentation. The Phase 14 button still proxies source.click().
    source = getattr(page, "create_character_button", None)
    if _valid(source):
        source.hide()
        parent = source.parentWidget()
        if _valid(parent):
            parent.hide()

    action_host = getattr(page, "new_build_action_host", None)
    if _valid(action_host):
        action_host.hide()

    create_button = getattr(page, "phase14_create_build_button", None)
    if _valid(create_button):
        create_button.show()

    splitter = getattr(page, "splitter", None)
    if not _valid(splitter) or splitter.count() < 2:
        return

    library = splitter.widget(0)
    inspector = splitter.widget(1)
    if _valid(library):
        library.show()
        library.setMinimumWidth(700)
    if _valid(inspector):
        inspector.show()
        inspector.setMinimumWidth(500)

    splitter.show()
    splitter.setChildrenCollapsible(False)
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 2)
    splitter.setSizes([900, 650])

    detail = getattr(page, "detail", None)
    if _valid(detail):
        detail.show()
        detail.setMinimumWidth(500)

    # Browsing should not look like an editor that was accidentally left open.
    for name in (
        "save_build_button",
        "cancel_build_button",
        "delete_build_button",
        "copy_build_button",
        "template_build_button",
        "save_button",
        "export_button",
    ):
        button = getattr(page, name, None)
        if _valid(button):
            button.hide()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import phase14_builds_command_center_support as command_center
    from ui.themed_builds_page import BuildsPage as ThemedBuildsPage

    original_wire = command_center._wire_new_build_button
    original_themed_build_ui = ThemedBuildsPage._build_ui

    def wire_target_new_build(page) -> None:
        original_wire(page)
        apply_phase14_build_visual_target(page)

    def build_themed_with_final_visual_target(self):
        original_themed_build_ui(self)
        # This is deliberately the outermost Builds presentation pass. Legacy wrappers
        # get to finish first; then the target geometry wins once, deterministically.
        apply_phase14_build_visual_target(self)

    command_center._wire_new_build_button = wire_target_new_build
    ThemedBuildsPage._build_ui = build_themed_with_final_visual_target
    _INSTALLED = True


__all__ = ["apply_phase14_build_visual_target", "install"]
