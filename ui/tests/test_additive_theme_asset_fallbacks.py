from pathlib import Path


def test_collectibles_use_dedicated_urban_wilderness_sheets_without_legacy_fallback() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert 'dashboard.SpriteRef("badges_1.png", 6, 4' in source
    assert 'dashboard.SpriteRef("badges_2.png", 3, 3' in source
    assert 'dashboard.SpriteRef("badges_3.png", 4, 1' in source
    assert '"urban_wilderness", "collectibles"' in source
    assert "return dedicated_badge(city_theme, city_badges.get(label))" in source
    assert '"Furnishing Plans": dashboard.SpriteRef("badges_3.png", 4, 1, 0)' in source
    assert '"Recipes": dashboard.SpriteRef("badges_3.png", 4, 1, 1)' in source
    assert '"Rumors": dashboard.SpriteRef("badges_3.png", 4, 1, 2)' in source
    assert '"Favors": dashboard.SpriteRef("badges_3.png", 4, 1, 3)' in source


def test_collectible_palette_uses_steel_amber_not_red_green_status_language() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert '"#7EA6B8"' in source
    assert '"#D0A35D"' in source
    assert 'overall_chunk="#7EA6B8"' in source
    assert "_CITY_BADGE_TONES" not in source


def test_collectible_badges_are_consistent_frameless_and_remove_sheet_spill() -> None:
    assets = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")
    presentation = Path("ui/collectibles_badge_presentation_support.py").read_text(encoding="utf-8")

    assert "def _keep_center_component" in assets
    assert "image = _keep_center_component(image)" in assets
    assert "def _clip_city_badge_for_display" in assets
    assert '"Companions": (0.00, 0.00, 0.00, 0.20)' in assets
    assert '"Hair": (0.00, 0.00, 0.00, 0.18)' in assets
    assert "return _clip_city_badge_for_display(" in assets
    assert "label.setFixedSize(90, 90)" in presentation
    assert "original_set_sprite(label, pixmap, 86)" in presentation
    assert 'background: transparent; border: none; padding: 0;' in presentation


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


def test_sidebar_brand_mark_returns_to_main_page() -> None:
    source = Path("ui/components/foundry_sidebar.py").read_text(encoding="utf-8")

    assert 'self.brand_mark.setCursor(Qt.CursorShape.PointingHandCursor)' in source
    assert 'self.brand_mark.setToolTip("Return to Main Page")' in source
    assert 'self.brand_mark.mousePressEvent = self._brand_mark_mouse_press' in source
    assert 'self.pageRequested.emit("operations_console")' in source
