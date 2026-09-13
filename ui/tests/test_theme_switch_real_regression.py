from pathlib import Path


def test_theme_switch_helper_is_wired_from_app() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "install_rylo_build_surface_theme_refresh" in source
