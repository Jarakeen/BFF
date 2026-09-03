from ui.collectibles_dashboard_page import (
    BADGE_SPRITES,
    CATEGORY_BADGE_INDEX,
    DASHBOARD_SPECS,
    NUMBER_SPRITES,
    CollectiblesDashboardPage,
    _percent,
    _progress_epithet,
)
from ui.components.foundry_sidebar import CORE_NAV_SECTIONS


def test_collectible_dashboard_percentage_does_not_complete_empty_category():
    assert _percent(0, 0) == 0
    assert _progress_epithet(0, 0) == "No catalog entries yet"


def test_collectible_dashboard_percentage_is_bounded_and_rounded():
    assert _percent(1, 3) == 33
    assert _percent(2, 3) == 67
    assert _percent(10, 5) == 100


def test_collectible_dashboard_starts_with_mockup_density_and_expandable_grid():
    assert len(DASHBOARD_SPECS) == 24
    assert CollectiblesDashboardPage.GRID_COLUMNS == 6
    assert {spec.meter for spec in DASHBOARD_SPECS} == {"bar", "ring", "shield", "vial"}
    assert len({spec.label for spec in DASHBOARD_SPECS}) == len(DASHBOARD_SPECS)


def test_collectible_dashboard_badges_follow_semantic_categories_not_card_positions():
    assert CATEGORY_BADGE_INDEX["Mounts"] == 0
    assert CATEGORY_BADGE_INDEX["Pets"] == 1
    assert CATEGORY_BADGE_INDEX["Armor Styles"] == 2
    assert CATEGORY_BADGE_INDEX["Hats"] == 3
    assert CATEGORY_BADGE_INDEX["Mementos"] == 9
    assert CATEGORY_BADGE_INDEX["Tools & Upgrades"] == 20
    assert CATEGORY_BADGE_INDEX["Customized Actions"] == 21
    assert "Weapon Styles" not in CATEGORY_BADGE_INDEX
    assert "Houses" not in CATEGORY_BADGE_INDEX
    assert "Fragments" not in CATEGORY_BADGE_INDEX


def test_collectible_dashboard_sprite_sheets_use_user_theme_asset_paths():
    assert NUMBER_SPRITES.path.name == "numbers.png"
    assert BADGE_SPRITES.path.name == "badges.png"
    assert NUMBER_SPRITES.path.parent.name == "collectibles"
    assert BADGE_SPRITES.path.parent.name == "collectibles"


def test_collections_sidebar_header_routes_to_dashboard():
    section = next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == "Collections"
    )
    assert section["page"] == "collectibles"
    assert ("Mounts", "collectibles:Mounts") in section["children"]
    assert ("Pets", "collectibles:Pets") in section["children"]
    assert ("Armor Styles", "collectibles:Armor Styles") in section["children"]
