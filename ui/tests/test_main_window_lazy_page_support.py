from pathlib import Path

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
