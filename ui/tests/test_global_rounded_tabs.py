from pathlib import Path

from ui import build_workspace_tab_layout_fix


def test_theme_application_appends_shared_file_folder_tab_geometry() -> None:
    source = Path(build_workspace_tab_layout_fix.__file__).read_text(encoding="utf-8")

    assert "ThemeManager.apply = apply_with_rounded_tabs" in source
    assert "QTabBar::tab" in source
    assert "border-top-left-radius: 9px" in source
    assert "border-top-right-radius: 9px" in source
    assert "border-bottom-left-radius: 0px" in source
    assert "border-bottom-right-radius: 0px" in source
    assert "border-radius: 9px" not in source
    assert "app.setStyleSheet(stylesheet" in source
