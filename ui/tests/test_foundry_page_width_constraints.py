from pathlib import Path

from ui import foundry_page


def test_foundry_page_does_not_force_top_level_window_width() -> None:
    source = Path(foundry_page.__file__).read_text(encoding="utf-8")

    assert "def minimumSizeHint(self) -> QSize:" in source
    assert "return QSize(0, hint.height())" in source


def test_foundry_workspace_uses_horizontal_scroll_when_content_is_wide() -> None:
    source = Path(foundry_page.__file__).read_text(encoding="utf-8")

    assert (
        "self.workspace_scroll.setHorizontalScrollBarPolicy("
        "Qt.ScrollBarPolicy.ScrollBarAsNeeded)"
    ) in source
    assert "self.workspace_scroll.setMinimumWidth(0)" in source
