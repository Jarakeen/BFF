from ui.components import foundry_sidebar
from ui.raid_engine_dashboard_support import _install_sidebar_route


def test_raid_engine_navigation_exposes_raid_plans_first() -> None:
    _install_sidebar_route()

    section = next(
        row
        for row in foundry_sidebar.CORE_NAV_SECTIONS
        if isinstance(row, dict) and row.get("label") == "Raid Engine"
    )

    assert section.get("page") == "raid_engine_dashboard"
    assert section.get("children", [])[0] == ("Raid Plans", "raid_plans")
