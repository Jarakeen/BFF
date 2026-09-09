from __future__ import annotations

"""Register the Raid Engine dashboard with the existing MainWindow.

Kept as a support layer so the dashboard can be added without duplicating or
replacing the long-lived Raid Engine pages it summarizes.
"""

_INSTALLED = False
_ORIGINAL_BUILD_UI = None


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

    _ORIGINAL_BUILD_UI = MainWindow.build_ui
    MainWindow.build_ui = _build_ui_with_raid_engine_dashboard
    _INSTALLED = True
