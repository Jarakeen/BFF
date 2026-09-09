from __future__ import annotations

"""Register the Raid Engine dashboard with the existing MainWindow.

Kept as a support layer so the dashboard can be added without duplicating or
replacing the long-lived Raid Engine pages it summarizes.
"""

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_DASHBOARD_REFRESH_PATCHED = False


def _install_sidebar_route() -> None:
    """Make the Raid Engine category header open the dashboard."""
    from ui.components import foundry_sidebar

    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if isinstance(section, dict) and section.get("label") == "Raid Engine":
            section["page"] = "raid_engine_dashboard"
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


def _build_ui_with_raid_engine_dashboard(self) -> None:
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)

    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage

    page = RaidEngineDashboardPage()
    page.set_sources(
        comp_builder=self.pages.get("comp_builder"),
        optimization=self.pages.get("console:6"),
        coverage=self.pages.get("console:7"),
        encounters=self.pages.get("console:1"),
        performance=self.pages.get("console:3"),
    )
    page.pageRequested.connect(self.show_page)
    page.sendTeamRequested.connect(self._send_optimized_team_to_roster)
    page.helpRequested.connect(lambda: _open_dashboard_help(self))

    self.pages["raid_engine_dashboard"] = page
    container = self.wrap_page(page)
    self.page_containers["raid_engine_dashboard"] = container
    self.stack.addWidget(container)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI
    if _INSTALLED:
        return

    from ui.main_window import MainWindow

    _install_sidebar_route()
    _install_read_only_dashboard_refresh()
    from ui.raid_engine_dashboard_polish_support import install as install_dashboard_polish
    install_dashboard_polish()
    _ORIGINAL_BUILD_UI = MainWindow.build_ui
    MainWindow.build_ui = _build_ui_with_raid_engine_dashboard
    _INSTALLED = True
