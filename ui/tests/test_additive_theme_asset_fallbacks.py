from pathlib import Path


def test_collectibles_use_dedicated_urban_wilderness_sheets_without_legacy_fallback() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert 'dashboard.SpriteRef("badges_1.png", 6, 4' in source
    assert 'dashboard.SpriteRef("badges_2.png", 3, 3' in source
    assert '"urban_wilderness", "collectibles"' in source
    assert "return dedicated_badge(city_theme, city_badges.get(label))" in source
    assert "Never fall back to old badge art" in source


def test_collectible_palette_uses_steel_amber_not_red_green_status_language() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert '"#7EA6B8"' in source
    assert '"#D0A35D"' in source
    assert 'overall_chunk="#7EA6B8"' in source
    assert "_CITY_BADGE_TONES" not in source


def test_collectible_badges_are_large_frameless_and_trim_sheet_spill() -> None:
    source = Path("ui/collectibles_badge_presentation_support.py").read_text(encoding="utf-8")

    assert "image.width() * 0.075" in source
    assert "label.setFixedSize(132, 132)" in source
    assert "original_set_sprite(label, pixmap, 128)" in source
    assert 'background: transparent; border: none; padding: 0;' in source


def test_roster_dashboard_uses_dedicated_theme_assets() -> None:
    source = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert '"urban_wilderness", "roster", "roster_badges.png"' in source
    assert '"urban_wilderness", "roster", "back_arrow.png"' in source
    assert '"roster-players"' not in source
    assert "from ui.ux_icons import icon" not in source


def test_urban_wilderness_branding_uses_only_approved_bff_logo() -> None:
    source = Path("ui/theme_brand_mark_support.py").read_text(encoding="utf-8")

    assert '_LOGO = ("assets", "logos", "BFF_logo.png")' in source
    assert "self.brand_mark.setFixedSize(228, 152)" in source
    assert "def build_ui_with_brand" in source
    assert 'label.property("sidebarLogo")' in source
    assert 'label.property("sidebarOffice")' in source
    assert "label.setParent(None)" in source
    assert Path("assets/logos/BFF_logo.png").is_file()
