from pathlib import Path


def test_rylo_surface_refresh_module_exists() -> None:
    assert Path("ui/rylo_build_surface_theme_refresh.py").exists()
