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
    """Gear slot editor whose selectable fields support substring search."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for combo in (self.set_combo, self.trait_combo, self.enchant_combo):
            _configure_search(combo)


class SearchableSkillBarRow(EligibleSkillBarRow):
    """Eligible skill bar with substring search."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            _configure_search(field)


def install() -> None:
    """Install shared selector behavior into the existing build editor."""
    build_editor.GearSlotRow = SearchableGearSlotRow
    build_editor.SkillBarRow = SearchableSkillBarRow
    build_editor.BuildEditor = EligibleBuildEditor
