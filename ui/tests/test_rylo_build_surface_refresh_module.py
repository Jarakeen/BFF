from pathlib import Path


def test_build_surface_refresh_module_preserves_foundry_teal() -> None:
    source = Path("ui/rylo_build_surface_theme_refresh.py").read_text(encoding="utf-8")
    assert 'return "#121315" if app.property("visualTheme") == VISUAL_THEME_RYLO else "#0C171B"' in source
