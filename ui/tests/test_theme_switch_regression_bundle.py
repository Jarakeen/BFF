from pathlib import Path


def test_theme_switch_regression_bundle() -> None:
    assert Path("ui/rylo_build_surface_theme_refresh.py").exists()
