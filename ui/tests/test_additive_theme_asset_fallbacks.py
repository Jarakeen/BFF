from pathlib import Path


def test_collectibles_additive_themes_never_hide_badges_when_optional_sheet_is_missing() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert "def dedicated_badge(theme, ref):" in source
    assert "if not path.is_file():" in source
    assert "return None" in source
    assert "original_badge_sprite(dashboard.BFF_THEME, label)" in source
    assert "original_badge_sprite(dashboard.RYLO_THEME, label)" in source
    assert "_recolor_badge(legacy" in source


def test_city_collectible_palette_uses_steel_amber_not_red_status_language() -> None:
    source = Path("ui/collectibles_new_theme_assets_support.py").read_text(encoding="utf-8")

    assert '"#7EA6B8"' in source
    assert '"#D0A35D"' in source
    assert '_CITY_BADGE_TONES' in source
    assert 'overall_chunk="#7EA6B8"' in source


def test_new_roster_art_has_visible_legacy_fallback_until_optional_jpg_pack_exists() -> None:
    source = Path("ui/themed_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert "def _legacy_sketch(self)" in source
    assert '"roster_rylo_sketch.svg"' in source
    assert '"roster_foundry_sketch.svg"' in source
    assert "Path(candidate).is_file() else self._legacy_sketch()" in source


def test_city_theme_uses_city_brand_mark_without_mutating_legacy_rylo_mark() -> None:
    source = Path("ui/theme_brand_mark_support.py").read_text(encoding="utf-8")

    assert "VISUAL_THEME_RYLO_CITY" in source
    assert 'filename = "sidebar_city_rylo.svg"' in source
    assert 'filename = "sidebar_scythe_rylo.svg"' in source
    assert "is_rylo_visual_theme" in source
