from __future__ import annotations

"""Final Phase 14 Builds presentation polish.

The mockup has one New Build action inside the library command row and a persistent
right-hand inspector. Older Easy Mode/header decorators still expose their original
entry button because it remains the canonical action source. This layer keeps that
source alive but hides its legacy header chrome so the page does not show two New
Build buttons.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import phase14_builds_command_center_support as command_center

    original_wire = command_center._wire_new_build_button

    def wire_target_new_build(page) -> None:
        original_wire(page)

        source = getattr(page, "create_character_button", None)
        if source is not None:
            # The Phase 14 button proxies source.click(), so hiding the legacy
            # presentation does not replace or duplicate creation behavior.
            source.hide()
            parent = source.parentWidget()
            if parent is not None:
                parent.hide()

        # The read-first dossier must always remain present beside the library.
        detail = getattr(page, "detail", None)
        if detail is not None:
            detail.show()
            detail.setMinimumWidth(500)

        splitter = getattr(page, "splitter", None)
        if splitter is not None and splitter.count() >= 2:
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 2)
            splitter.setSizes([820, 620])

    command_center._wire_new_build_button = wire_target_new_build
    _INSTALLED = True


__all__ = ["install"]
