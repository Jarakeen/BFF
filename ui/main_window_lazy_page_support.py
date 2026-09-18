from __future__ import annotations

"""Defer independent MainWindow pages until their first navigation.

The Foundry has accumulated several expensive page constructors.  This support
layer keeps the current MainWindow/page contracts intact while replacing only a
small, dependency-light set with placeholders during startup.  The real page is
constructed once, swapped into the same stack position, and then reused for the
rest of the application session.
"""

from collections.abc import Callable
from time import perf_counter

from PySide6.QtWidgets import QWidget


_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_PAGE = None

# Keep pages with build-time cross-wiring eager. In particular, Rotation is now
# a release-visible primary workspace with a dense decorator/runtime graph, so
# constructing it during MainWindow setup is safer than first-click materialization.
# operations_console is the startup destination and Rotation remains eager
# because its decorated runtime graph is not safe to materialize on first click.
# Achievement profile state is now owned independently from the page, so the
# heavy Achievements browser can be deferred safely.
LAZY_PAGE_SPECS: dict[str, str] = {
    "achievements": "AchievementsPage",
    "collectibles_browser": "CollectiblesPage",
    "gear_lookup": "GearLookupPage",
    "stickerbook": "StickerbookPage",
    "timers": "AsylumPerfectaTimerPage",
    "community_news": "CommunityNewsPage",
    "incident": "IncidentPage",
}


class _LazyPagePlaceholder(QWidget):
    """Cheap stack occupant used until a deferred page is first requested."""

    def __init__(self, page_key: str) -> None:
        super().__init__()
        self.page_key = str(page_key)


def _construct_lazy_page(
    factory: Callable[[], QWidget],
    page_key: str,
    *,
    window=None,
) -> QWidget:
    """Construct a deferred page without performing known throwaway first work."""
    kwargs = {}
    if page_key == "collectibles_browser" and window is not None:
        service = getattr(window, "collectible_service", None)
        if service is not None:
            kwargs["service"] = service

    if page_key not in {"stickerbook", "collectibles_browser"}:
        return factory(**kwargs)

    # StickerbookPage and CollectiblesPage both refresh from __init__(), but
    # their first navigation immediately selects/synchronizes the requested
    # profile/category and refreshes again. Suppress only that throwaway pass.
    # first navigation immediately synchronizes the active Achievements profile
    # and refreshes again.  Suppress only that constructor refresh so the first
    # database read/population is for the profile the user actually has active.
    refresh = getattr(factory, "refresh", None)
    if not callable(refresh):
        return factory()

    setattr(factory, "refresh", lambda self: None)
    try:
        return factory(**kwargs)
    finally:
        setattr(factory, "refresh", refresh)


def _materialize_page(window, page_key: str):
    factories: dict[str, Callable[[], QWidget]] = getattr(
        window, "_lazy_page_factories", {}
    )
    factory = factories.get(page_key)
    current = window.pages.get(page_key)
    if factory is None or not isinstance(current, _LazyPagePlaceholder):
        return current

    started = perf_counter()
    page = _construct_lazy_page(factory, page_key, window=window)
    container = window.wrap_page(page)
    old_container = window.page_containers.get(page_key)
    old_index = window.stack.indexOf(old_container) if old_container is not None else -1

    if old_index >= 0:
        window.stack.insertWidget(old_index, container)
        window.stack.removeWidget(old_container)
        old_container.deleteLater()
    else:
        window.stack.addWidget(container)

    window.pages[page_key] = page
    window.page_containers[page_key] = container
    factories.pop(page_key, None)

    elapsed_ms = (perf_counter() - started) * 1000.0
    print(f"[FoundryDock PERF] first load {page_key}: {elapsed_ms:.1f} ms")
    return page


def _build_ui_with_lazy_pages(self) -> None:
    assert _ORIGINAL_BUILD_UI is not None

    from ui import main_window

    original_classes: dict[str, type[QWidget]] = {}
    for page_key, attribute_name in LAZY_PAGE_SPECS.items():
        page_class = getattr(main_window, attribute_name)
        original_classes[page_key] = page_class
        setattr(
            main_window,
            attribute_name,
            lambda *args, _page_key=page_key, **kwargs: _LazyPagePlaceholder(_page_key),
        )

    try:
        _ORIGINAL_BUILD_UI(self)
    finally:
        for page_key, attribute_name in LAZY_PAGE_SPECS.items():
            setattr(main_window, attribute_name, original_classes[page_key])

    self._lazy_page_factories = dict(original_classes)
    # OperationsConsole already calls refresh() from its constructor.  The app
    # immediately navigates to it as the startup destination, so suppress just
    # that first redundant navigation refresh.  Future visits refresh normally.
    self._operations_console_initial_navigation_pending = True


def _show_page_without_method(
    window,
    page_name: str,
    page_key: str,
    method_name: str,
):
    """Run normal navigation while suppressing one page refresh-style method."""
    assert _ORIGINAL_SHOW_PAGE is not None
    page = window.pages.get(page_key)
    method = getattr(page, method_name, None)
    if not callable(method):
        return _ORIGINAL_SHOW_PAGE(window, page_name)

    had_instance_method = method_name in getattr(page, "__dict__", {})
    prior_instance_method = page.__dict__.get(method_name) if had_instance_method else None
    setattr(page, method_name, lambda: None)
    try:
        return _ORIGINAL_SHOW_PAGE(window, page_name)
    finally:
        if had_instance_method:
            setattr(page, method_name, prior_instance_method)
        else:
            delattr(page, method_name)


def _show_page_without_refresh(window, page_name: str, page_key: str):
    return _show_page_without_method(window, page_name, page_key, "refresh")


def _show_page_with_lazy_materialization(self, page_name: str):
    assert _ORIGINAL_SHOW_PAGE is not None
    requested_key = str(page_name or "")
    page_key = (
        "collectibles_browser"
        if requested_key.startswith("collectibles:")
        else requested_key
    )
    was_lazy = isinstance(self.pages.get(page_key), _LazyPagePlaceholder)
    _materialize_page(self, page_key)

    if (
        page_key == "operations_console"
        and getattr(self, "_operations_console_initial_navigation_pending", False)
    ):
        self._operations_console_initial_navigation_pending = False
        return _show_page_without_refresh(self, page_name, "operations_console")

    # AchievementsPage builds and refreshes its complete browser in __init__().
    # MainWindow's normal achievements navigation also refreshes, so reuse the
    # constructor state on the first lazy visit instead of doing the same DB work twice.
    if page_key == "achievements" and was_lazy:
        return _show_page_without_refresh(self, page_name, "achievements")

    # GearLookupPage performs its canonical database refresh in __init__().
    # Its ordinary navigation path also refreshes, so the very first lazy visit
    # would otherwise read and repopulate the same catalog twice. Later visits
    # retain the existing refresh behavior.
    if page_key == "gear_lookup" and was_lazy:
        return _show_page_without_refresh(self, page_name, "gear_lookup")

    # The vAS+2 timer constructor finishes with _refresh(), while its navigation
    # hook calls refresh_context(), which is just another _refresh().  Reuse the
    # constructor state on first materialization and keep later context refreshes.
    if page_key == "timers" and was_lazy:
        return _show_page_without_method(
            self,
            page_name,
            "timers",
            "refresh_context",
        )

    return _ORIGINAL_SHOW_PAGE(self, page_name)


def install() -> None:
    """Install low-risk lazy page construction around the completed UI stack."""
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_SHOW_PAGE
    if _INSTALLED:
        return

    from ui.main_window import MainWindow

    _ORIGINAL_BUILD_UI = MainWindow.build_ui
    _ORIGINAL_SHOW_PAGE = MainWindow.show_page
    MainWindow.build_ui = _build_ui_with_lazy_pages
    MainWindow.show_page = _show_page_with_lazy_materialization
    _INSTALLED = True
