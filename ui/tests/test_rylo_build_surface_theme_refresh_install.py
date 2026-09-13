from pathlib import Path


def test_build_surface_theme_refresh_installs_after_rylo_surface_fix() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    import_token = "install_rylo_build_surface_theme_refresh"
    assert import_token in source
    assert source.index("install_rylo_surface_icon_fix(app)") < source.index("install_rylo_build_surface_theme_refresh(app)")
