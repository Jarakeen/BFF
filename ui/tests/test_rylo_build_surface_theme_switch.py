from pathlib import Path


def test_rylo_build_workspace_surface_refreshes_on_theme_switch() -> None:
    source = Path("ui/rylo_build_surface_theme_refresh.py").read_text(encoding="utf-8")

    assert 'themeAwareBuildSurface' in source
    assert '"#0C171B"' in source
    assert '"#121315"' in source
    assert 'for widget in app.allWidgets()' in source
    assert 'refresh_theme_aware_build_surfaces' in source


def test_rylo_final_nav_override_is_not_red() -> None:
    source = Path("ui/rylo_surface_icon_fix.py").read_text(encoding="utf-8")

    nav_block = source.split('/* Checked navigation:', 1)[1].split('/* Final item selection', 1)[0]
    assert '#8B1E24' not in nav_block
    assert '#281719' not in nav_block
    assert '#6FA8D3' in nav_block
