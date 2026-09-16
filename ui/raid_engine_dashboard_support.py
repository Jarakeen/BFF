from __future__ import annotations

"""Register raid-planning surfaces with the existing application window.

This module is the explicit application-composition boundary for the rebuilt
raid-lead workspace. It keeps long-lived engine ownership intact while exposing
the City After Midnight RAID workflow as Roster -> Plans -> Assignments ->
Readiness -> Live Raid.
"""

import warnings

_INSTALLED = False


def _install_canonical_sidebar_routes() -> None:
    """Expose the audited raid-lead navigation using only currently real routes."""
    from ui.components import foundry_sidebar

    def existing_dict(label: str):
        for section in foundry_sidebar.CORE_NAV_SECTIONS:
            if isinstance(section, dict) and section.get("label") == label:
                return section
        return None

    def existing_leaf(label: str):
        for section in foundry_sidebar.CORE_NAV_SECTIONS:
            if isinstance(section, tuple) and section and section[0] == label:
                return section
        return None

    collectibles = existing_dict("Collectibles")
    tools = existing_dict("Tool") or existing_dict("Tools")
    achievements = existing_leaf("Achievements") or ("Achievements", "achievements")
    community = existing_leaf("Community News") or ("Community News", "community_news")
    settings = existing_leaf("Settings") or ("Settings", "settings")

    sections: list = [
        {
            "label": "Raid",
            "children": [
                ("Roster", "roster_workspace"),
                ("Raid Plans", "raid_plans"),
                ("Assignments", "assignments"),
                ("Readiness", "readiness"),
                ("Live Raid", "live_raid"),
            ],
        },
        {
            "label": "Build",
            "children": [
                ("Builds", "console:2"),
                ("Rotation Builder", "rotations"),
                ("Extreme Builder", "extreme_optimization"),
            ],
        },
        {
            "label": "Encounter",
            "children": [
                ("Encounters", "console:1"),
                ("Mechanics & Timelines", "console:4"),
            ],
        },
        {
            "label": "Team",
            "children": [
                ("Coverage", "console:7"),
                ("Comp Maker", "comp_builder"),
                ("Optimizer Adviser", "console:6"),
            ],
        },
        {
            "label": "Review",
            "children": [
                ("Top Gear", "console:3"),
            ],
        },
        achievements,
    ]
    if collectibles is not None:
        sections.append(collectibles)
    if tools is not None:
        tools = dict(tools)
        tools["label"] = "Tools"
        sections.append(tools)
    sections.extend((community, settings))

    foundry_sidebar.CORE_NAV_SECTIONS[:] = sections


def _install_safe_dashboard_rewire() -> None:
    """Avoid PySide's noisy RuntimeWarning when a button has no slots to remove."""
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
        help_page.show_topic("comp_builder")


def _open_raid_plan_coverage(window, plan) -> None:
    coverage = window.pages.get("console:7")
    if coverage is None or not hasattr(coverage, "set_raid_plan_scope"):
        return
    coverage.set_raid_plan_scope(plan)
    window.show_page("console:7")


def _open_raid_plan_rotation(window, plan, seat_id: str) -> None:
    rotation = window.pages.get("rotations")
    if rotation is None:
        return
    from ui.raid_plan_rotation_handoff_support import bind_raid_plan_rotation_page

    try:
        bind_raid_plan_rotation_page(rotation, raid_plan=plan, seat_id=seat_id)
    except (OSError, TypeError, ValueError) as exc:
        raid_plans = window.pages.get("raid_plans")
        status = getattr(raid_plans, "status", None)
        if status is not None:
            status.warning(f"Could not open Raid Plan spot in Rotation: {exc}")
        return
    window.show_page("rotations")


def _open_raid_plan_adviser(window, plan) -> None:
    adviser = window.pages.get("console:6")
    if adviser is None or not hasattr(adviser, "set_raid_plan_adviser_scope"):
        return
    try:
        adviser.set_raid_plan_adviser_scope(plan)
    except (OSError, TypeError, ValueError) as exc:
        raid_plans = window.pages.get("raid_plans")
        status = getattr(raid_plans, "status", None)
        if status is not None:
            status.warning(f"Could not review Raid Plan in Optimizer Adviser: {exc}")
        return
    window.show_page("console:6")


def _register_page(window, route: str, page) -> None:
    window.pages[route] = page
    container = window.wrap_page(page)
    window.page_containers[route] = container
    window.stack.addWidget(container)


def _register_roster_workspace_refresh(window, page) -> None:
    """Reload canonical roster/build state whenever the visible Roster is opened."""

    def prepare_roster(route: str) -> None:
        if route != "roster_workspace":
            return
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()
        refresh_assets = getattr(page, "refresh_theme_assets", None)
        if callable(refresh_assets):
            refresh_assets()

    window.sidebar.pageRequested.connect(prepare_roster)


def register_raid_engine_pages(window) -> None:
    """Register the complete City RAID workflow after source engine pages exist."""
    from ui.city_live_raid_page import CityLiveRaidPage
    from ui.city_raid_assignments_page import CityRaidAssignmentsPage
    from ui.city_raid_plan_workspace_page import CityRaidPlanWorkspacePage
    from ui.city_raid_readiness_page import CityRaidReadinessPage
    from ui.city_raid_roster_workspace_page import CityRaidRosterWorkspacePage
    from ui.raid_engine_dashboard_page import RaidEngineDashboardPage

    roster_workspace = CityRaidRosterWorkspacePage()
    _register_page(window, "roster_workspace", roster_workspace)
    _register_roster_workspace_refresh(window, roster_workspace)

    assignments = CityRaidAssignmentsPage()
    assignments.pageRequested.connect(window.show_page)
    _register_page(window, "assignments", assignments)

    readiness = CityRaidReadinessPage()
    readiness.pageRequested.connect(window.show_page)
    _register_page(window, "readiness", readiness)

    live_raid = CityLiveRaidPage()
    live_raid.pageRequested.connect(window.show_page)
    _register_page(window, "live_raid", live_raid)

    dashboard = RaidEngineDashboardPage()
    dashboard.set_sources(
        comp_builder=window.pages.get("comp_builder"),
        optimization=window.pages.get("console:6"),
        coverage=window.pages.get("console:7"),
        encounters=window.pages.get("console:1"),
        performance=window.pages.get("console:3"),
    )
    dashboard.pageRequested.connect(window.show_page)
    dashboard.sendTeamRequested.connect(window._send_optimized_team_to_roster)
    dashboard.helpRequested.connect(lambda: _open_dashboard_help(window))
    _register_page(window, "raid_engine_dashboard", dashboard)

    raid_plans = CityRaidPlanWorkspacePage()
    raid_plans.pageRequested.connect(window.show_page)
    raid_plans.coverageRequested.connect(lambda plan: _open_raid_plan_coverage(window, plan))
    raid_plans.rotationRequested.connect(
        lambda plan, seat_id: _open_raid_plan_rotation(window, plan, seat_id)
    )
    raid_plans.adviserRequested.connect(lambda plan: _open_raid_plan_adviser(window, plan))
    _register_page(window, "raid_plans", raid_plans)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.build_screenshot_import_disable_support import (
        install as install_build_screenshot_import_disable_support,
    )
    from ui.coverage_raid_plan_scope_support import install as install_coverage_raid_plan_scope_support
    from ui.raid_plan_optimizer_adviser_support import install as install_raid_plan_optimizer_adviser_support

    # CoveragePage and OptimizationPage are created by the original build_ui,
    # so extend both classes before that UI is constructed.
    install_coverage_raid_plan_scope_support()
    install_raid_plan_optimizer_adviser_support()
    _install_canonical_sidebar_routes()
    from ui.raid_engine_dashboard_polish_support import install as install_dashboard_polish
    install_dashboard_polish()
    _install_safe_dashboard_rewire()
    install_build_screenshot_import_disable_support()
    _INSTALLED = True
