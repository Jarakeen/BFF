from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QCompleter

from engine.config import get_resource_path
from services.skill_bar_eligibility import filter_skill_choices


class SkillPicker(QComboBox):
    """Flat, searchable ESO skill picker shared by Builds and Optimization.

    The list is alphabetical and deliberately not nested. Each base ability
    and each morph is a separate choice; rank progression is collapsed.
    ItemData stores the full structured record so the selected ability_id and
    morph identity survive past the display name.
    """

    def __init__(self, skill_choices=None, *, slot_index: int = 0, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.all_skill_choices = [s for s in (skill_choices or []) if isinstance(s, dict)]
        self._class = ""
        self._vampire = False
        self._werewolf = False
        self._form = None
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setDuplicatesEnabled(False)
        self.setMinimumHeight(38)
        self.setIconSize(QSize(26, 26))
        self.setToolTip("Ultimate" if slot_index == 5 else f"Skill {slot_index + 1}")
        self.lineEdit().setClearButtonEnabled(True)
        self._rebuild()

    def set_context(self, *, character_class: str | None = None, vampire: bool = False,
                    werewolf: bool = False, transformed_form: str | None = None) -> None:
        self._class = character_class or ""
        self._vampire = bool(vampire)
        self._werewolf = bool(werewolf)
        self._form = transformed_form
        self._rebuild()

    def set_slot(self, slot_index: int) -> None:
        self.slot_index = slot_index
        self.setToolTip("Ultimate" if slot_index == 5 else f"Skill {slot_index + 1}")
        self._rebuild()

    def _rebuild(self) -> None:
        current_id = self.currentData(Qt.ItemDataRole.UserRole)
        current_text = self.currentText().strip()
        choices = filter_skill_choices(
            self.all_skill_choices,
            character_class=self._class,
            slot_index=self.slot_index,
            vampire=self._vampire,
            werewolf=self._werewolf,
            transformed_form=self._form,
        )

        self.blockSignals(True)
        self.clear()
        self.addItem("")
        for skill in choices:
            name = str(skill.get("name") or "").strip()
            if not name:
                continue
            self.addItem(name, skill)
            texture = str(skill.get("texture") or "").strip()
            if texture:
                icon_name = texture.replace("\\", "/").rsplit("/", 1)[-1]
                if "." in icon_name:
                    icon_name = icon_name.rsplit(".", 1)[0] + ".png"
                self.setItemIcon(self.count() - 1, self._icon(icon_name))

        # Recreate the completer after every model rebuild so it points at
        # the current filtered model.
        completer = QCompleter(self.model(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)

        restored = False
        if current_id is not None:
            index = self.findData(current_id, Qt.ItemDataRole.UserRole)
            if index >= 0:
                self.setCurrentIndex(index)
                restored = True
        if not restored and current_text:
            index = self.findText(current_text, Qt.MatchFlag.MatchExactly)
            self.setCurrentIndex(index if index >= 0 else 0)
        self.blockSignals(False)

    @staticmethod
    def _icon(filename: str) -> QIcon:
        from pathlib import Path
        root = get_resource_path("assets", "AbilityIcons", "icons", "128")
        path = root / filename
        return QIcon(str(path)) if path.exists() else QIcon()
