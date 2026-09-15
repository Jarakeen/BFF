from __future__ import annotations

"""Register Raid Engine planning surfaces with the existing MainWindow.

The dashboard remains a read-mostly summary. The Raid Plans workspace owns the
visible persistent trial plan without replacing the long-lived Roster, Comp Maker,
Coverage, Encounter, or Optimization pages.
"""

import warnings

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_DASHBOARD_REFRESH_PATCHED = False


def _install_sidebar_route() -> None:
    """Make Raid Engine open the dashboard and expose Raid Plans as a child route."""
    from ui.components import foundry_sidebar

    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if not isinstance(section, dict) or section.get("label") != "Raid Engine":
            continue
        section["page"] = "raid_engine_dashboard"
        children = list(section.get("children") or ())
        if ("Raid Plans", "raid_plans") not in children:
            children.insert(0, ("Raid Plans", "raid_plans"))
        section["children"] = children
        return


def _install_read_only_dashboard_refresh() -> None:
    """Do not let visiting the dashboard re-autofill Team Optimization.

    OptimizationPage.refresh() rebuilds its editor. The dashboard is a summary
    surface, so it must never mutate that working team merely because the user
    opened the Raid Engine landing page.
    """
    global _DASHBOARD_REFRESH_PATCHED
    if _DASHBOARD_REFRESH_PATCHED:
        return

    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage

    original_refresh = RaidEngineDashboardPage.refresh

    def refresh_without_optimization_reset(self) -> None:
        page = getattr(self, "optimization", None)
        if page is None:
            original_refresh(self)
            return

        had_instance_refresh = "refresh" in getattr(page, "__dict__", {})
        prior_instance_refresh = page.__dict__.get("refresh") if had_instance_refresh else None
        page.refresh = lambda: None
        try:
            original_refresh(self)
        finally:
            if had_instance_refresh:
                page.refresh = prior_instance_refresh
            else:
                delattr(page, "refresh")

    RaidEngineDashboardPage.refresh = refresh_without_optimization_reset
    _DASHBOARD_REFRESH_PATCHED = True


def _install_safe_dashboard_rewire() -> None:
    """Avoid PySide's noisy RuntimeWarning when a button has no slots to remove.

    Disconnecting an unconnected signal is harmless, but libpyside emits a warning
    before the Python exception guard can handle it. Keep the existing rewire
    semantics while suppressing only that specific warning.
    """
    from ui import raid_engine_dashboard_polish_support as polish

    def safe_rewire(button, callback) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"libpyside: Failed to disconnect.*",
                category=RuntimeWarning,
            )
            try:
                button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
        button.clicked.connect(lambda *_: callback())

    polish._rewire_button = safe_rewire


def _open_dashboard_help(window) -> None:
    settings = window.pages.get("settings")
    if settings is None:
        return
    window.show_page("settings")
    help_page = getattr(settings, "help_page", None)
    help_index = getattr(settings, "help_section_index", None)
    if help_page is not None and help_index is not None:
        settings._show_section(help_index)
        # The existing Comp Builder guide is the closest workflow-level topic
        # until a dedicated dashboard help article is added.
        help_page.show_topic("comp_builder")


def _register_page(window, route: str, page) -> None:
    window.pages[route] = page
    container = window.wrap_page(page)
    window.page_containers[route] = container
    window.stack.addWidget(container)


def _build_ui_with_raid_engine_dashboard(self) -> None:
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)

    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage
    from ui.raid_plan_persistence_page import RaidPlanPersistencePage

    dashboard = RaidEngineDashboardPage()
    dashboard.set_sources(
        comp_builder=self.pages.get("comp_builder"),
        optimization=self.pages.get("console:6"),
        coverage=self.pages.get("console:7"),
        encounters=self.pages.get("console:1"),
        performance=self.pages.get("console:3"),
    )
    dashboard.pageRequested.connect(self.show_page)
    dashboard.sendTeamRequested.connect(self._send_optimized_team_to_roster)
    dashboard.helpRequested.connect(lambda: _open_dashboard_help(self))
    _register_page(self, "raid_engine_dashboard", dashboard)

    raid_plans = RaidPlanPersistencePage()
    raid_plans.pageRequested.connect(self.show_page)
    _register_page(self, "raid_plans", raid_plans)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI
    if _INSTALLED:
        return

    from ui.main_window import MainWindow
    from ui.build_screenshot_import_disable_support import (
        install as install_build_screenshot_import_disable_support,
    )

    _install_sidebar_route()
    _install_read_only_dashboard_refresh()
    from ui.raid_engine_dashboard_polish_support import install as install_dashboard_polish
    install_dashboard_polish()
    _install_safe_dashboard_rewire()
    # Keep the screenshot/OCR intake implementation in the tree but remove its
    # user-facing Builds control while the new planning/intake ownership settles.
    install_build_screenshot_import_disable_support()
    _ORIGINAL_BUILD_UI = MainWindow.build_ui
    MainWindow.build_ui = _build_ui_with_raid_engine_dashboard
    _INSTALLED = True
