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


def test_builds_keeps_editor_at_top_with_centered_entry_button_and_inline_form() -> None:
    source = _source()

    assert 'FoundryButton("+ Create a New Build"' in source
    assert "self.new_build_action_host = QWidget(self.workspace_widget)" in source
    assert "new_build_action_layout.addStretch(1)" in source
    assert "self.workspace_layout.insertWidget(insertion_index, self.new_build_action_host)" in source
    assert "self.workspace_layout.insertWidget(insertion_index + 1, self.new_build_panel)" in source
    assert "self.save_button.hide()" in source
    assert 'self.setObjectName("newBuildPullDown")' in source
    assert 'title = QLabel("Build something worth bringing to raid.")' in source
    assert 'FoundryButton("Create & Open Build"' in source
    assert "tabs.setCurrentIndex(1)" in source


def test_build_editor_uses_one_save_action_and_no_nested_new_build_action() -> None:
    source = _source()

    assert 'button.text() == "+ Add New Build"' in source
    assert "add_build.deleteLater()" in source
    assert 'save.setText("Save Build")' in source
    assert "row.addWidget(cancel)" in source
    assert "row.addWidget(save)" in source


def test_build_editor_save_preserves_non_editor_build_state() -> None:
    source = _source()

    assert "for field_name in _EDITOR_OWNED_BUILD_FIELDS" in source
    assert "setattr(saved_build, field_name, getattr(edited_build, field_name))" in source
    assert '"ScribedSkills"' not in source.split("_EDITOR_OWNED_BUILD_FIELDS = (", 1)[1].split(")", 1)[0]
    assert '"ScribedSkillRecipes"' not in source.split("_EDITOR_OWNED_BUILD_FIELDS = (", 1)[1].split(")", 1)[0]
    assert '"ClassSkillLines"' not in source.split("_EDITOR_OWNED_BUILD_FIELDS = (", 1)[1].split(")", 1)[0]
    assert '"ClassMasteryAbilityIds"' not in source.split("_EDITOR_OWNED_BUILD_FIELDS = (", 1)[1].split(")", 1)[0]
    assert '"SecondMundus"' not in source.split("_EDITOR_OWNED_BUILD_FIELDS = (", 1)[1].split(")", 1)[0]


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
    assert page.header.context_layout.itemAt(0).widget() is button
    assert page.header.context_layout.itemAt(1).widget().isAncestorOf(page.trial_label)
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


def test_builds_button_is_centered_above_workspace(monkeypatch) -> None:
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
    assert page.header.context_layout.indexOf(button) == -1
    assert page.workspace_layout.itemAt(0).widget() is page.new_build_action_host
    assert page.workspace_layout.itemAt(1).widget() is page.new_build_panel
    assert page.workspace_layout.itemAt(2).widget() is page.splitter
    assert page.new_build_action_host.isAncestorOf(button)

    page.resize(1450, 600)
    page.show()
    app.processEvents()
    button_center = button.mapToGlobal(button.rect().center()).x()
    host_center = page.new_build_action_host.mapToGlobal(
        page.new_build_action_host.rect().center()
    ).x()
    assert abs(button_center - host_center) <= 10
    assert page.splitter.isVisible()


def test_overview_cards_reflow_without_sideways_scroll_at_desktop_widths():
    from PySide6.QtWidgets import QApplication

    from models.build_model import BuildRoster, PlayerBuild
    from ui.components.foundry_card import FoundryCard
    from ui.foundry_page import FoundryPage
    from ui.operations_console import CORE_COVERAGE, OperationsConsole

    app = QApplication.instance() or QApplication([])
    character_creation_easy_mode_support.install()
    page = OperationsConsole.__new__(OperationsConsole)
    FoundryPage.__init__(page)
    page.expedition = SimpleNamespace(
        expedition=SimpleNamespace(Expedition="Dreadsail Reef", Difficulty="Veteran Hardmode", Objective="Reef Guardian")
    )
    page._build_ui()
    page.roster = BuildRoster(Members=[PlayerBuild(
        Name="Rylo and the long name", BuildName="Corpsebuster Damage Dealer",
        Role="Damage Dealer", EsoClass="Necromancer",
    )])
    page._capability_audits = {}
    page._coverage = lambda: (
        {name: "unverified" for name in CORE_COVERAGE},
        {name: [] for name in CORE_COVERAGE},
    )
    page._key_stats_card = lambda _build: FoundryCard("Key Stats")
    page._raid_schedule_card = lambda _build: FoundryCard("Raid Schedule")
    page._skills_to_work_on_card = lambda _build: FoundryCard("Next Raid Focus")
    page._render()

    for width in (1100, 1200, 1366, 1600, 1918, 1100):
        page.resize(width, 800)
        page.show()
        app.processEvents()
        app.processEvents()
        assert page.workspace_scroll.horizontalScrollBar().maximum() == 0
        assert all(len(row) == 4 and len({card.y() for card in row}) == 1 for row in (
            page._hero_cards, page._detail_cards, page._goal_cards,
        ))