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

# Keep pages with build-time cross-wiring eager.  In particular,
# operations_console is the startup destination, Achievements supplies the
# active profile used by Collectibles, and Raid Engine source pages are still
# composed together by existing support layers.
LAZY_PAGE_SPECS: dict[str, str] = {
    "rotations": "CanonicalRotationDashboardPage",
    "gear_lookup": "GearLookupPage",
    "stickerbook": "StickerbookPage",
    "community_news": "CommunityNewsPage",
    "incident": "IncidentPage",
}


class _LazyPagePlaceholder(QWidget):
    """Cheap stack occupant used until a deferred page is first requested."""

    def __init__(self, page_key: str) -> None:
        super().__init__()
        self.page_key = str(page_key)


def _materialize_page(window, page_key: str):
    factories: dict[str, Callable[[], QWidget]] = getattr(
        window, "_lazy_page_factories", {}
    )
    factory = factories.get(page_key)
    current = window.pages.get(page_key)
    if factory is None or not isinstance(current, _LazyPagePlaceholder):
        return current

    started = perf_counter()
    page = factory()
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
            lambda _page_key=page_key: _LazyPagePlaceholder(_page_key),
        )

    try:
        _ORIGINAL_BUILD_UI(self)
    finally:
        for page_key, attribute_name in LAZY_PAGE_SPECS.items():
            setattr(main_window, attribute_name, original_classes[page_key])

    self._lazy_page_factories = dict(original_classes)


def _show_page_with_lazy_materialization(self, page_name: str):
    assert _ORIGINAL_SHOW_PAGE is not None
    _materialize_page(self, str(page_name or ""))
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
