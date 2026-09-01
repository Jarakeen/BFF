from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QCompleter

from engine.config import get_resource_path
from widgets import build_editor
from ui.components.eligible_build_editor import EligibleBuildEditor, EligibleSkillBarRow
from services.skill_choice_service import load_skill_choices

ASSET_ROOT = get_resource_path("assets", "AbilityIcons", "icons", "128")


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
    combo.setIconSize(QSize(26, 26))


def _icon_for_skill(skill: dict) -> QIcon:
    texture = str(skill.get("texture", "") or "").strip()
    if not texture:
        return QIcon()
    filename = Path(texture.replace("\\", "/")).name
    local = ASSET_ROOT / Path(filename).with_suffix(".png")
    return QIcon(str(local)) if local.exists() else QIcon()


def _compact_set_label(value: str) -> str:
    """Shorten Perfected in gear selectors without changing canonical set names."""
    text = str(value or "")
    return "Perf. " + text[len("Perfected "):] if text.startswith("Perfected ") else text


class SearchableGearSlotRow(build_editor.GearSlotRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quality_combo.setFixedWidth(82)
        for combo in (self.set_combo, self.set2_combo):
            self._compact_set_combo(combo)
        for combo in (self.set_combo, self.trait_combo, self.enchant_combo):
            _configure_search(combo)

    @staticmethod
    def _compact_set_combo(combo: QComboBox) -> None:
        current = combo.currentText().strip()
        for index in range(combo.count()):
            canonical = combo.itemText(index)
            combo.setItemData(index, canonical, Qt.UserRole)
            combo.setItemText(index, _compact_set_label(canonical))
        if current:
            canonical_index = combo.findData(current, Qt.UserRole)
            if canonical_index >= 0:
                combo.setCurrentIndex(canonical_index)

    @staticmethod
    def _canonical_set_text(combo: QComboBox) -> str:
        text = combo.currentText().strip()
        index = combo.currentIndex()
        if index >= 0 and combo.itemText(index).strip() == text:
            canonical = combo.itemData(index, Qt.UserRole)
            if canonical is not None:
                return str(canonical).strip()
        if text.startswith("Perf. "):
            return "Perfected " + text[len("Perf. "):]
        return text

    @property
    def value(self):
        slot = super().value
        slot.Set = self._canonical_set_text(self.set_combo)
        slot.Set2 = self._canonical_set_text(self.set2_combo)
        return slot

    def load(self, slot):
        super().load(slot)
        for combo, canonical in (
            (self.set_combo, slot.Set or ""),
            (self.set2_combo, getattr(slot, "Set2", "") or ""),
        ):
            match = combo.findData(canonical, Qt.UserRole)
            if match >= 0:
                combo.setCurrentIndex(match)
            else:
                combo.setCurrentText(_compact_set_label(canonical))


class SearchableSkillBarRow(EligibleSkillBarRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            _configure_search(field)


def _patch_builds_page() -> None:
    """Patch live Builds-page selectors and canonical Phase 2 gear summaries."""
    from ui.builds_page import BuildsPage
    from ui.components.builds_page_phase2_display import (
        build_status_rows,
        gear_card,
        set_bonus_card,
    )
    from widgets.build_editor import BuildEditor

    def _editor(self):
        cache = getattr(self, "_build_editor_reference_cache", None)
        if cache is None:
            cache = {
                "race_choices": self.reference.list_race_names(),
                "set_choices": self.reference.list_gear_set_names(),
                "skill_choices": load_skill_choices(self.reference.database.database),
                "cp_choices": [
                    c
                    for c in self.reference.list_champion_points()
                    if isinstance(c, dict) and c.get("name")
                ],
                "food_choices": self.reference.list_food_names(),
                "potion_choices": self.reference.list_potion_names(),
            }
            self._build_editor_reference_cache = cache
        return BuildEditor(**cache)

    BuildsPage._editor = _editor
    BuildsPage._gear_card = gear_card
    BuildsPage._set_bonus_card = set_bonus_card
    BuildsPage._status_rows = lambda _self, build: build_status_rows(build)


def _patch_optimization_skill_picker() -> None:
    """Give the Optimization Test Lab the same searchable morph choices."""
    from ui.components.custom_roster_lab import CustomRosterLabWidget

    def _populate_skill_choices(self):
        current_id = self.skill_combo.currentData() if hasattr(self, "skill_combo") else None
        self.skill_combo.blockSignals(True)
        self.skill_combo.clear()
        try:
            selected_class = self.class_combo.currentText().strip()
        except AttributeError:
            selected_class = ""

        choices = load_skill_choices(self.build_lab.database_path)
        seen: set[tuple[int, int]] = set()
        from services.skill_bar_eligibility import is_eligible
        for skill in sorted(choices, key=lambda s: (str(s.get("name") or "").casefold(), int(s.get("morph") or 0))):
            if not (
                is_eligible(skill, character_class=selected_class, slot_index=0)
                or is_eligible(skill, character_class=selected_class, slot_index=5)
            ):
                continue
            key = (int(skill.get("base_ability_id") or skill.get("ability_id") or 0), int(skill.get("morph") or 0))
            if key in seen:
                continue
            seen.add(key)
            name = str(skill.get("name") or "").strip()
            self.skill_combo.addItem(name, int(skill.get("ability_id")))
            icon = _icon_for_skill(skill)
            if not icon.isNull():
                self.skill_combo.setItemIcon(self.skill_combo.count() - 1, icon)

        self.skill_combo.setIconSize(QSize(26, 26))
        if current_id is not None:
            index = self.skill_combo.findData(current_id)
            if index >= 0:
                self.skill_combo.setCurrentIndex(index)
        self.skill_combo.blockSignals(False)

    CustomRosterLabWidget._populate_skill_choices = _populate_skill_choices


def install() -> None:
    """Install shared selector behavior before pages construct BuildEditor."""
    build_editor.GearSlotRow = SearchableGearSlotRow
    build_editor.SkillBarRow = SearchableSkillBarRow
    build_editor.BuildEditor = EligibleBuildEditor
    _patch_builds_page()
    _patch_optimization_skill_picker()
