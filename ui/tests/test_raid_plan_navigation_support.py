from ui.components import foundry_sidebar
from ui.raid_engine_dashboard_support import _install_canonical_sidebar_routes


def test_raid_lead_navigation_exposes_current_planning_workspaces() -> None:
    original = list(foundry_sidebar.CORE_NAV_SECTIONS)
    try:
        _install_canonical_sidebar_routes()

        raid = next(
            row
            for row in foundry_sidebar.CORE_NAV_SECTIONS
            if isinstance(row, dict) and row.get("label") == "Raid"
        )
        build = next(
            row
            for row in foundry_sidebar.CORE_NAV_SECTIONS
            if isinstance(row, dict) and row.get("label") == "Build"
        )
        team = next(
            row
            for row in foundry_sidebar.CORE_NAV_SECTIONS
            if isinstance(row, dict) and row.get("label") == "Team"
        )

        assert raid.get("children", [])[:4] == [
            ("Raid Dashboard", "raid_engine_dashboard"),
            ("Raid Plans", "raid_plans"),
            ("Assignments", "assignments"),
            ("Readiness", "readiness"),
        ]
        assert ("Roster", "roster_workspace") in team.get("children", [])
        assert ("Rotation Builder", "rotations") in build.get("children", [])
        assert ("Extreme Builder", "extreme_optimization") in build.get("children", [])
        assert ("Coverage", "console:7") in team.get("children", [])
        assert ("Comp Builder", "comp_builder") in team.get("children", [])
        assert ("Optimizer Adviser", "console:6") in team.get("children", [])
    finally:
        foundry_sidebar.CORE_NAV_SECTIONS[:] = original
