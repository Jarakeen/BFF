from pathlib import Path

from ui import build_progression_scroll_fix


def test_embedded_progression_unwraps_inner_scroll_areas() -> None:
    source = Path(build_progression_scroll_fix.__file__).read_text(encoding="utf-8")

    assert "isinstance(page, QScrollArea)" in source
    assert "content = page.takeWidget()" in source
    assert "tabs.removeTab(index)" in source
    assert "tabs.insertTab(index, content, icon, title)" in source


def test_scroll_fix_only_wraps_builds_progression_loader() -> None:
    source = Path(build_progression_scroll_fix.__file__).read_text(encoding="utf-8")

    assert "original_load_progression = BuildsPage._load_progression_tab" in source
    assert "BuildsPage._load_progression_tab = load_progression_without_inner_scroll" in source
