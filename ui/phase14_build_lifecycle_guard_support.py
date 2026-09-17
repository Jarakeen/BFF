from __future__ import annotations

"""Guard Phase 14 Builds against stale Qt objects during legacy wrapper startup.

FoundryDock still has several BuildsPage decorators that assume the original splitter
geometry. During construction one of those legacy wrappers can dispose a Phase 14
command-center child after the command center has stored it on the page. PySide keeps
the Python wrapper, but the underlying C++ object is gone. This layer fails closed
while that happens and, after the complete build-ui chain returns, reconstructs the
command center once if its Qt objects were invalidated.

No build data or database state is touched here. This is UI lifetime repair only.
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


def _command_center_alive(page) -> bool:
    return all(
        _valid(getattr(page, name, None))
        for name in (
            "phase14_library_tabs",
            "phase14_build_table",
            "phase14_build_search",
            "phase14_class_filter",
            "phase14_role_filter",
            "phase14_content_filter",
            "phase14_create_build_button",
        )
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui import phase14_build_profile_support as profile_support
    from ui import phase14_builds_command_center_support as command_center

    original_build_ui = BuildsPage._build_ui
    original_set_filters = command_center._set_filters_from_library
    original_populate = command_center._populate_build_table

    def safe_template_mode(page) -> bool:
        if not _command_center_alive(page):
            # Treat a stale command center as unavailable while constructor-time
            # legacy wrappers finish. Returning True makes downstream inspector /
            # profile decorators skip Phase 14 widget work instead of dereferencing
            # deleted Qt objects.
            return True
        tabs = page.phase14_library_tabs
        index = tabs.currentIndex()
        return bool(index >= 0 and tabs.tabText(index) == "Templates")

    def safe_active_library_mode(page) -> str:
        if not _command_center_alive(page):
            return "All"
        tabs = page.phase14_library_tabs
        index = tabs.currentIndex()
        if index < 0:
            return "All"
        return str(tabs.tabText(index) or "All")

    def safe_set_filters(page) -> None:
        if not _command_center_alive(page):
            return
        original_set_filters(page)

    def safe_populate(page) -> None:
        if not _command_center_alive(page):
            return
        original_populate(page)

    def safe_profile_matches_mode(page, build) -> bool:
        mode = safe_active_library_mode(page)
        profile = profile_support._profile(page, build)
        if mode == "Archive":
            return profile.archived
        if profile.archived:
            return False
        if mode == "Mine":
            return profile.ownership == "mine"
        if mode == "Team":
            return profile.ownership == "team"
        if mode == "Favorites":
            return profile.favorite
        return mode == "All"

    command_center._template_mode = safe_template_mode
    command_center._active_library_mode = safe_active_library_mode
    command_center._set_filters_from_library = safe_set_filters
    command_center._populate_build_table = safe_populate
    profile_support._profile_matches_mode = safe_profile_matches_mode

    def build_ui_with_lifecycle_repair(self):
        original_build_ui(self)
        if _command_center_alive(self):
            return

        # A legacy wrapper invalidated the first command center. Rebuild only the
        # presentation surface after the full wrapper chain has returned, when no
        # inner decorator can still delete its children.
        replacement = command_center._create_command_center(self)
        current = self.splitter.widget(0)
        displaced = self.splitter.replaceWidget(0, replacement)
        stale = displaced if displaced is not None else current
        if stale is not None and stale is not replacement and _valid(stale):
            stale.hide()
            stale.setParent(self)

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([860, 650])
        command_center._wire_new_build_button(self)
        command_center._quiet_overview_action_bar(self)

    BuildsPage._build_ui = build_ui_with_lifecycle_repair
    _INSTALLED = True


__all__ = ["install"]
