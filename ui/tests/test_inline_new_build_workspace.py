from pathlib import Path
from types import SimpleNamespace

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


def test_builds_keeps_editor_at_top_with_header_entry_button_and_inline_form() -> None:
    source = _source()

    assert 'FoundryButton("+ Create a New Build"' in source
    assert "self.header.context_layout.addWidget(" in source
    assert "self.workspace_layout.insertWidget(insertion_index, self.new_build_panel)" in source
    assert "button_host" not in source
    assert 'self.setObjectName("newBuildPullDown")' in source
    assert 'title = QLabel("Build something worth bringing to raid.")' in source
    assert 'FoundryButton("Create & Open Build"' in source
    assert "tabs.setCurrentIndex(1)" in source


def test_overview_button_opens_same_inline_form_without_navigating_away() -> None:
    source = _source()

    assert "console.layout.insertWidget(0, panel)" in source
    assert "status_host=console" in source
    assert "on_created=console.refresh" in source
    assert "show_page(\"console:2\")" not in source


def test_overview_new_build_button_sits_in_header_and_raid_status_is_full_height(monkeypatch) -> None:
    from PySide6.QtWidgets import QApplication, QFrame, QSizePolicy

    from models.build_model import BuildRoster
    from ui.components.foundry_card import FoundryCard
    from ui.foundry_page import FoundryPage
    from ui.operations_console import OperationsConsole

    app = QApplication.instance() or QApplication([])
    character_creation_easy_mode_support.install()
    page = OperationsConsole.__new__(OperationsConsole)
    FoundryPage.__init__(page)
    page.expedition = SimpleNamespace(
        expedition=SimpleNamespace(Expedition="", Difficulty="", Objective="")
    )
    page.roster = BuildRoster()
    page._build_ui()
    button = page.create_character_button
    assert page.header.context_layout.itemAt(2).widget() is button
    assert page.header.context_layout.itemAt(3).widget().isAncestorOf(page.player_combo)
    assert button.text() == "+ Create a New Build"

    card = page._raid_status_card()
    assert isinstance(card, FoundryCard)
    assert card.title_label.text() == "Raid Status"
    assert not card.isAncestorOf(button)
    assert card.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

    page.resize(1450, 600)
    page.show()
    app.processEvents()
    button_bottom = button.mapToGlobal(button.rect().bottomLeft()).y()
    selector_bottom = page.player_combo.mapToGlobal(
        page.player_combo.rect().bottomLeft()
    ).y()
    assert abs(button_bottom - selector_bottom) <= 10

    class InlineForm(QFrame):
        def __init__(self, *, page, status_host, on_created, parent):
            super().__init__(parent)
            self.setVisible(False)

        def open_for_creation(self):
            self.setVisible(True)

    monkeypatch.setattr(character_creation_easy_mode_support, "CharacterCreationEasyModePanel", InlineForm)
    page.pages = {"console:2": object()}
    page.layout.addWidget(card)
    button.click()
    assert page.layout.itemAt(0).widget() is page._overview_new_build_panel
    assert page.layout.itemAt(1).widget() is card
    assert page._overview_new_build_panel.isVisible()


def test_builds_button_shares_selector_row_without_displacing_workspace(monkeypatch) -> None:
    from PySide6.QtWidgets import QApplication, QFrame

    from ui.builds_page import BuildsPage
    from ui.foundry_page import FoundryPage

    app = QApplication.instance() or QApplication([])
    character_creation_easy_mode_support.install()

    class InlineForm(QFrame):
        def __init__(self, *, page, parent):
            super().__init__(parent)
            self.setVisible(False)

        def open_for_creation(self):
            self.setVisible(True)

    monkeypatch.setattr(
        character_creation_easy_mode_support, "CharacterCreationEasyModePanel", InlineForm
    )
    page = BuildsPage.__new__(BuildsPage)
    FoundryPage.__init__(page)
    page._list_trials = lambda: ["Current Raid"]
    page._build_ui()

    button = page.create_character_button
    assert page.header.context_layout.itemAt(2).widget() is button
    assert page.workspace_layout.itemAt(0).widget() is page.new_build_panel
    assert page.workspace_layout.itemAt(1).widget() is page.splitter

    page.resize(1450, 600)
    page.show()
    app.processEvents()
    button_bottom = button.mapToGlobal(button.rect().bottomLeft()).y()
    selector_bottom = page.trial_combo.mapToGlobal(
        page.trial_combo.rect().bottomLeft()
    ).y()
    assert abs(button_bottom - selector_bottom) <= 10
    assert page.splitter.isVisible()
