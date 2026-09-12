from pathlib import Path

from ui import character_creation_easy_mode_support


def _source() -> str:
    return Path(character_creation_easy_mode_support.__file__).read_text(encoding="utf-8")


def test_new_build_creation_is_inline_not_modal() -> None:
    source = _source()

    assert "class CharacterCreationEasyModePanel(QFrame)" in source
    assert 'self.workspace_layout.insertWidget' in source
    assert "dialog.exec()" not in source
    assert "QDialog" not in source


def test_new_build_workspace_is_prominent_and_routes_to_edit_after_creation() -> None:
    source = _source()

    assert 'title = QLabel("Build something worth bringing to raid.")' in source
    assert 'FoundryButton("+ Start a New Build"' in source
    assert 'FoundryButton("Create & Open Build"' in source
    assert "tabs.setCurrentIndex(1)" in source
