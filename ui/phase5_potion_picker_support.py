from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

from models.build_model import PlayerBuild
from services.potion_choice_service import PotionChoiceService

_INSTALLED = False


def _choices():
    processed = Path(__file__).resolve().parents[1] / "data" / "processed" / "alchemy_effects.json"
    return PotionChoiceService(processed).list_choices()


def _configure_combo(combo) -> None:
    current = str(combo.currentText() or "").strip()
    combo.blockSignals(True)
    combo.clear()
    combo.setEditable(False)
    combo.addItem("", "")
    for choice in _choices():
        combo.addItem(choice.label, choice.canonical_id)
        index = combo.count() - 1
        combo.setItemData(
            index,
            f"{choice.formula_count} verified reagent formula(s)",
            Qt.ItemDataRole.ToolTipRole,
        )
    if current:
        combo.addItem(current, current)
        combo.setCurrentIndex(combo.count() - 1)
    combo.blockSignals(False)


def _select_saved(combo, saved_value: str) -> None:
    value = str(saved_value or "").strip()
    if not value:
        combo.setCurrentIndex(0)
        return
    for index in range(combo.count()):
        if str(combo.itemData(index) or "").strip().casefold() == value.casefold():
            combo.setCurrentIndex(index)
            return
    # Legacy/free-text values remain loadable and round-trip without mutation.
    combo.addItem(value, value)
    combo.setCurrentIndex(combo.count() - 1)


def _persisted_value(combo) -> str:
    data = str(combo.currentData() or "").strip()
    return data or str(combo.currentText() or "").strip()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.build_editor import BuildEditor

    original_skills_card = BuildEditor._build_skills_card
    original_load = BuildEditor.load
    original_model = BuildEditor.model

    def skills_card_with_canonical_potions(self):
        card = original_skills_card(self)
        _configure_combo(self.potion)
        self.potion.setToolTip(
            "Canonical crafted-potion effect family. Equivalent reagent recipes are grouped; selecting a potion does not imply uptime."
        )
        return card

    def load_with_canonical_potions(self, model: PlayerBuild) -> None:
        original_load(self, model)
        _select_saved(self.potion, str(model.Potion or ""))

    def model_with_canonical_potions(self) -> PlayerBuild:
        build = original_model.fget(self)
        build.Potion = _persisted_value(self.potion)
        return build

    BuildEditor._build_skills_card = skills_card_with_canonical_potions
    BuildEditor.load = load_with_canonical_potions
    BuildEditor.model = property(model_with_canonical_potions)

    _INSTALLED = True
