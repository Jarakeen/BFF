from ui.collectibles_dashboard_page import _percent, _progress_epithet
from ui.components.foundry_sidebar import CORE_NAV_SECTIONS


def test_collectible_dashboard_percentage_does_not_complete_empty_category():
    assert _percent(0, 0) == 0
    assert _progress_epithet(0, 0) == "No catalog entries yet"


def test_collectible_dashboard_percentage_is_bounded_and_rounded():
    assert _percent(1, 3) == 33
    assert _percent(2, 3) == 67
    assert _percent(10, 5) == 100


def test_collections_sidebar_header_routes_to_dashboard():
    section = next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == "Collections"
    )
    assert section["page"] == "collectibles"
    assert ("Mounts", "collectibles:Mounts") in section["children"]
    assert ("Pets", "collectibles:Pets") in section["children"]
    assert ("Armor Styles", "collectibles:Armor Styles") in section["children"]
