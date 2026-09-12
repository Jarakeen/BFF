from pathlib import Path

from ui import build_workspace_tab_layout_fix


def test_theme_application_appends_shared_rounded_tab_geometry() -> None:
    source = Path(build_workspace_tab_layout_fix.__file__).read_text(encoding="utf-8")

    assert "ThemeManager.apply = apply_with_rounded_tabs" in source
    assert "QTabBar::tab" in source
    assert "border-radius: 9px" in source
    assert "app.setStyleSheet(stylesheet" in source
