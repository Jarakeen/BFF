from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter

from widgets import build_editor
from ui.components.eligible_build_editor import EligibleBuildEditor, EligibleSkillBarRow


def _configure_search(combo: QComboBox) -> None:
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.setDuplicatesEnabled(False)
    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    combo.lineEdit().setClearButtonEnabled(True)


class SearchableGearSlotRow(build_editor.GearSlotRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for combo in (self.set_combo, self.trait_combo, self.enchant_combo):
            _configure_search(combo)


class SearchableSkillBarRow(EligibleSkillBarRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            _configure_search(field)


def _patch_builds_page() -> None:
    """Make Builds pass structured ability records to the eligible picker."""
    from ui.builds_page import BuildsPage
    from widgets.build_editor import BuildEditor

    def _editor(self):
        return BuildEditor(
            race_choices=self.reference.list_race_names(),
            set_choices=self.reference.list_gear_set_names(),
            skill_choices=[s for s in self.reference.list_skills() if isinstance(s, dict) and s.get("name")],
            cp_choices=[c for c in self.reference.list_champion_points() if isinstance(c, dict) and c.get("name")],
        )

    BuildsPage._editor = _editor


def install() -> None:
    """Install shared selector behavior before pages construct BuildEditor."""
    build_editor.GearSlotRow = SearchableGearSlotRow
    build_editor.SkillBarRow = SearchableSkillBarRow
    build_editor.BuildEditor = EligibleBuildEditor
    _patch_builds_page()
