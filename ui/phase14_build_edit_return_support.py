from __future__ import annotations

"""Return Phase 14 Build editing to the command-center library.

The legacy inline editor remains the canonical edit surface, but Save/Cancel are
navigation actions from the Phase 14 inspector. After either action completes,
return to the Builds library and reassert the read-first inspector instead of
leaving the user stranded on the legacy Edit workspace.
"""

_INSTALLED = False


def _return_to_library(page) -> None:
    tabs = getattr(page, "build_tabs", None)
    if tabs is not None and tabs.count() > 0:
        tabs.setCurrentIndex(0)

    # Reapply the Phase 14 presentation at the boundary after legacy edit code
    # has finished refreshing selectors/roster state.
    try:
        from ui.phase14_build_visual_target_support import apply_phase14_build_visual_target
        apply_phase14_build_visual_target(page)
    except Exception:
        pass

    try:
        from ui.phase14_build_inspector_support import _render_inspector
        _render_inspector(page)
    except Exception:
        pass


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_save = BuildsPage._save_edit_tab
    original_cancel = BuildsPage._cancel_edit_tab

    def save_and_return(self) -> None:
        original_save(self)
        _return_to_library(self)

    def cancel_and_return(self) -> None:
        original_cancel(self)
        _return_to_library(self)

    BuildsPage._save_edit_tab = save_and_return
    BuildsPage._cancel_edit_tab = cancel_and_return
    _INSTALLED = True


__all__ = ["install"]
