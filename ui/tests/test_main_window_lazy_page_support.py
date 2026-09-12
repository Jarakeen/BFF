from pathlib import Path
from types import SimpleNamespace

import ui.main_window_lazy_page_support as lazy_support
from ui.main_window_lazy_page_support import LAZY_PAGE_SPECS


def test_lazy_page_set_is_limited_to_dependency_light_pages():
    assert LAZY_PAGE_SPECS == {
        "rotations": "CanonicalRotationDashboardPage",
        "gear_lookup": "GearLookupPage",
        "stickerbook": "StickerbookPage",
        "community_news": "CommunityNewsPage",
        "incident": "IncidentPage",
    }

    # Startup and cross-wired Raid Engine/profile pages remain eager in this
    # first performance pass.
    for eager_page in (
        "operations_console",
        "achievements",
        "collectibles",
        "collectibles_browser",
        "roster_page",
        "comp_builder",
        "console:1",
        "console:2",
        "console:3",
        "console:4",
        "console:6",
        "console:7",
        "console:8",
        "settings",
    ):
        assert eager_page not in LAZY_PAGE_SPECS


def test_lazy_materialization_replaces_placeholder_once_and_caches_page():
    source = Path("ui/main_window_lazy_page_support.py").read_text(encoding="utf-8")

    assert "window.stack.insertWidget(old_index, container)" in source
    assert "window.stack.removeWidget(old_container)" in source
    assert "window.pages[page_key] = page" in source
    assert "window.page_containers[page_key] = container" in source
    assert "factories.pop(page_key, None)" in source


def test_lazy_bootstrap_wraps_completed_startup_stack_and_roster_stays_home():
    dd_support = Path("ui/performance_dashboard_dd_support.py").read_text(encoding="utf-8")
    app_source = Path("app.py").read_text(encoding="utf-8")

    assert "install_role_surface()" in dd_support
    assert "install_lazy_pages()" in dd_support
    assert dd_support.index("install_role_surface()") < dd_support.index("install_lazy_pages()")
    assert 'window.show_page("operations_console")' in app_source


def test_startup_roster_overview_reuses_constructor_refresh_then_refreshes_later(monkeypatch):
    calls = []

    class Page:
        def refresh(self):
            calls.append("refresh")

    page = Page()
    window = SimpleNamespace(
        pages={"operations_console": page},
        _lazy_page_factories={},
        _operations_console_initial_navigation_pending=True,
    )

    def original_show_page(self, page_name):
        if page_name == "operations_console":
            self.pages[page_name].refresh()
        return page_name

    monkeypatch.setattr(lazy_support, "_ORIGINAL_SHOW_PAGE", original_show_page)

    assert lazy_support._show_page_with_lazy_materialization(
        window, "operations_console"
    ) == "operations_console"
    assert calls == []
    assert window._operations_console_initial_navigation_pending is False

    assert lazy_support._show_page_with_lazy_materialization(
        window, "operations_console"
    ) == "operations_console"
    assert calls == ["refresh"]


def test_first_lazy_gear_lookup_reuses_constructor_refresh_then_refreshes_later(monkeypatch):
    calls = []

    class Placeholder:
        pass

    class Page:
        def refresh(self):
            calls.append("refresh")

    page = Page()
    window = SimpleNamespace(
        pages={"gear_lookup": Placeholder()},
        _lazy_page_factories={"gear_lookup": object()},
        _operations_console_initial_navigation_pending=False,
    )

    def materialize(self, page_name):
        self.pages[page_name] = page
        self._lazy_page_factories.pop(page_name, None)
        return page

    def original_show_page(self, page_name):
        if page_name == "gear_lookup":
            self.pages[page_name].refresh()
        return page_name

    monkeypatch.setattr(lazy_support, "_LazyPagePlaceholder", Placeholder)
    monkeypatch.setattr(lazy_support, "_materialize_page", materialize)
    monkeypatch.setattr(lazy_support, "_ORIGINAL_SHOW_PAGE", original_show_page)

    assert lazy_support._show_page_with_lazy_materialization(
        window, "gear_lookup"
    ) == "gear_lookup"
    assert calls == []

    assert lazy_support._show_page_with_lazy_materialization(
        window, "gear_lookup"
    ) == "gear_lookup"
    assert calls == ["refresh"]
