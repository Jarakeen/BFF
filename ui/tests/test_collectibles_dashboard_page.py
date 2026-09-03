from ui.collectibles_dashboard_page import (
    BFF_BADGES,
    BFF_THEME,
    DASHBOARD_SPECS,
    RYLO_BADGES,
    RYLO_THEME,
    CollectiblesDashboardPage,
    SpriteRef,
    SpriteSheet,
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


def test_bff_badges_use_base_and_expansion_sheets_by_semantic_category():
    assert BFF_BADGES["Mounts"] == SpriteRef("badges.png", 6, 4, 0, 0.06, 0.03)
    assert BFF_BADGES["Pets"].filename == "badges.png"
    assert BFF_BADGES["Weapon Styles"] == SpriteRef("badges_2.png", 3, 3, 1, 0.03, 0.03)
    assert BFF_BADGES["Skins"].filename == "badges_2.png"
    assert BFF_BADGES["Houses"].index == 2
    assert BFF_BADGES["Polymorphs"].index == 3
    assert BFF_BADGES["Facial Accessories"].index == 4
    assert BFF_BADGES["Fragments"].index == 5
    assert BFF_BADGES["Motifs"].index == 6
    assert BFF_BADGES["Antiquities"].index == 7
    assert BFF_BADGES["Lorebooks"].index == 8


def test_rylo_has_same_current_dashboard_category_art_contract():
    current_labels = {spec.label for spec in DASHBOARD_SPECS}
    # Weapon Styles awaits Rylo badges_2.png; every other current dashboard
    # category has a semantic red/black badge in Rylo's base sheet.
    assert current_labels - {"Weapon Styles"} <= set(RYLO_BADGES)
    assert RYLO_BADGES["Mounts"].filename == "badges.png"
    assert RYLO_BADGES["Houses"].index == 20
    assert RYLO_BADGES["Fragments"].index == 22
    assert RYLO_BADGES["Tools & Upgrades"].index == 23
    assert RYLO_BADGES["Weapon Styles"].filename == "badges_2.png"
    assert RYLO_BADGES["Motifs"].filename == "badges_2.png"
    assert RYLO_BADGES["Antiquities"].filename == "badges_2.png"
    assert RYLO_BADGES["Lorebooks"].filename == "badges_2.png"


def test_dashboard_themes_share_structure_but_not_visual_palette():
    assert BFF_THEME.folder == "Bff"
    assert RYLO_THEME.folder == "Rylo"
    assert len(BFF_THEME.accents) == len(RYLO_THEME.accents) == 6
    assert BFF_THEME.accents != RYLO_THEME.accents
    assert BFF_THEME.overall_chunk != RYLO_THEME.overall_chunk
    assert BFF_THEME.panel != RYLO_THEME.panel


def test_sprite_sheet_supports_arbitrary_grid_and_crop_insets(tmp_path):
    sheet = SpriteSheet(tmp_path / "missing.png", 3, 3, 0.03, 0.04)
    assert sheet.columns == 3
    assert sheet.rows == 3
    assert sheet.inset_x == 0.03
    assert sheet.inset_y == 0.04
    assert sheet.cell(-1) is None
    assert sheet.cell(9) is None


def test_collections_sidebar_header_routes_to_dashboard():
    section = next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == "Collections"
    )
    assert section["page"] == "collectibles"
    assert ("Mounts", "collectibles:Mounts") in section["children"]
    assert ("Pets", "collectibles:Pets") in section["children"]
    assert ("Armor Styles", "collectibles:Armor Styles") in section["children"]
