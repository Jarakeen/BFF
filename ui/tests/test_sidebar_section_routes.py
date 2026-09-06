from ui.components.foundry_sidebar import CORE_NAV_SECTIONS


def _section(label: str) -> dict:
    return next(
        item
        for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == label
    )


def test_roster_header_opens_operations_overview():
    assert _section("Roster").get("page") == "operations_console"


def test_raid_engine_header_is_group_only():
    assert "page" not in _section("Raid Engine")


def test_mechanics_header_is_group_only_and_child_opens_boss_mechanics():
    mechanics = _section("Mechanics")
    assert "page" not in mechanics
    assert ("Mechanics", "console:4") in mechanics["children"]
