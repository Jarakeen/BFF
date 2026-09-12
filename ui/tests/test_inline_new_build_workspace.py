from pathlib import Path

from ui import character_creation_easy_mode_support


def _source() -> str:
    return Path(character_creation_easy_mode_support.__file__).read_text(encoding="utf-8")


def test_new_build_creation_is_inline_not_modal() -> None:
    source = _source()

    assert "class CharacterCreationEasyModePanel(QFrame)" in source
    assert "dialog.exec()" not in source
    assert "QDialog" not in source
    assert "self.setVisible(False)" in source
    assert "self.setVisible(True)" in source


def test_builds_keeps_normal_layout_with_centered_entry_button_and_dropdown_form() -> None:
    source = _source()

    assert 'FoundryButton("+ Create a New Build"' in source
    assert "button_layout.addStretch(1)" in source
    assert "self.workspace_layout.insertWidget(insertion_index, button_host)" in source
    assert "self.workspace_layout.insertWidget(insertion_index + 1, self.new_build_panel)" in source
    assert 'self.setObjectName("newBuildPullDown")' in source
    assert 'title = QLabel("Build something worth bringing to raid.")' in source
    assert 'FoundryButton("Create & Open Build"' in source
    assert "tabs.setCurrentIndex(1)" in source


def test_overview_button_opens_same_inline_form_without_navigating_away() -> None:
    source = _source()

    assert "console.layout.insertWidget(1, panel)" in source
    assert "status_host=console" in source
    assert "on_created=console.refresh" in source
    assert "show_page(\"console:2\")" not in source


def test_overview_raid_status_card_stretches_with_neighbor_cards() -> None:
    source = _source()

    assert "card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)" in source
    assert "card.setMinimumHeight(255)" in source
    assert "card.body_layout.insertWidget(" in source
    assert "Qt.AlignmentFlag.AlignHCenter" in source
