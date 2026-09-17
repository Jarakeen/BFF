from __future__ import annotations

"""Guard Phase 14 Builds against stale or detached Qt objects.

FoundryDock still has several BuildsPage decorators that assume the original splitter
geometry. During construction an older wrapper can either dispose a Phase 14 child or
leave the command-center widgets alive but detached from the visible Roster tab. PySide
then gives us one of two equally charming outcomes: a deleted C++ object behind a live
Python wrapper, or a perfectly valid widget marooned outside the visible layout.

This layer fails closed while constructor-time wrappers run and performs a final
presentation-only repair after both the base BuildsPage chain and the themed BuildsPage
subclass chain have completed. No build data or database state is touched here.
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


def _command_center_attached(page) -> bool:
    """Return True only when the live command center is actually in splitter slot 0."""
    if not _command_center_alive(page):
        return False
    splitter = getattr(page, "splitter", None)
    if not _valid(splitter) or splitter.count() < 1:
        return False

    table = page.phase14_build_table
    current = table
    while _valid(current):
        parent = current.parentWidget()
        if parent is None:
            return False
        if parent is splitter:
            return splitter.widget(0) is current
        current = parent
    return False


def _show_library_workspace(page) -> None:
    """Make the library tab/splitter/detail visible without exposing editor chrome."""
    splitter = getattr(page, "splitter", None)
    if _valid(splitter):
        splitter.show()

    detail = getattr(page, "detail", None)
    if _valid(detail):
        detail.show()
        detail.setMinimumWidth(500)

    tabs = getattr(page, "build_tabs", None)
    if _valid(tabs) and tabs.count() > 0:
        tabs.show()
        if tabs.currentIndex() != 0:
            tabs.setCurrentIndex(0)
        roster_tab = tabs.widget(0)
        if _valid(roster_tab):
            roster_tab.show()


def _restore_inspector(page) -> None:
    """Render the selected build into the right-hand dossier after wrapper repair."""
    detail = getattr(page, "detail", None)
    detail_layout = getattr(page, "detail_layout", None)
    if not _valid(detail) or detail_layout is None:
        return
    if not getattr(page, "roster", None) or not getattr(page.roster, "Members", None):
        return

    if int(getattr(page, "selected_index", -1)) < 0:
        page.selected_index = 0

    try:
        from ui import phase14_build_inspector_support as inspector_support
        inspector_support._render_inspector(page)
    except RuntimeError:
        # Constructor-time Qt churn can still be in flight. A normal selection or
        # showEvent refresh will retry. Never turn a visual repair into a startup crash.
        return


def _repair_command_center(page, command_center) -> None:
    """Rebuild only the Phase 14 presentation surface when it is missing/detached."""
    splitter = getattr(page, "splitter", None)
    if not _valid(splitter):
        return

    if not _command_center_attached(page):
        replacement = command_center._create_command_center(page)
        replacement.show()
        current = splitter.widget(0) if splitter.count() else None
        if splitter.count():
            displaced = splitter.replaceWidget(0, replacement)
        else:
            splitter.insertWidget(0, replacement)
            displaced = None
        stale = displaced if displaced is not None else current
        if stale is not None and stale is not replacement and _valid(stale):
            stale.hide()
            stale.setParent(page)

        command_center._wire_new_build_button(page)
        command_center._quiet_overview_action_bar(page)

    # The desired Phase 14 composition is library left, inspector right. Reassert
    # that geometry after every wrapper chain instead of letting the old Roster page
    # quietly reclaim the whole width.
    if splitter.count() >= 2:
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 620])
        right = splitter.widget(1)
        if _valid(right):
            right.show()
            right.setMinimumWidth(500)

    _show_library_workspace(page)
    _restore_inspector(page)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage as BaseBuildsPage
    from ui.themed_builds_page import BuildsPage as ThemedBuildsPage
    from ui import phase14_build_profile_support as profile_support
    from ui import phase14_builds_command_center_support as command_center

    original_base_build_ui = BaseBuildsPage._build_ui
    original_themed_build_ui = ThemedBuildsPage._build_ui
    original_set_filters = command_center._set_filters_from_library
    original_populate = command_center._populate_build_table

    def safe_template_mode(page) -> bool:
        if not _command_center_attached(page):
            return True
        tabs = page.phase14_library_tabs
        index = tabs.currentIndex()
        return bool(index >= 0 and tabs.tabText(index) == "Templates")

    def safe_active_library_mode(page) -> str:
        if not _command_center_attached(page):
            return "All"
        tabs = page.phase14_library_tabs
        index = tabs.currentIndex()
        if index < 0:
            return "All"
        return str(tabs.tabText(index) or "All")

    def safe_set_filters(page) -> None:
        if not _command_center_attached(page):
            return
        original_set_filters(page)

    def safe_populate(page) -> None:
        if not _command_center_attached(page):
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

    def build_base_ui_with_lifecycle_repair(self):
        original_base_build_ui(self)
        _repair_command_center(self, command_center)

    def build_themed_ui_with_final_repair(self):
        original_themed_build_ui(self)
        _repair_command_center(self, command_center)

    BaseBuildsPage._build_ui = build_base_ui_with_lifecycle_repair
    ThemedBuildsPage._build_ui = build_themed_ui_with_final_repair
    _INSTALLED = True


__all__ = ["install"]
