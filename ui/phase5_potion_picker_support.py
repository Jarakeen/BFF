from __future__ import annotations

from PySide6.QtCore import Qt

from minmax.potion_availability_repository import DEFAULT_PROCESSED, LEGACY_PROCESSED
from models.build_model import PlayerBuild
from services.potion_choice_service import PotionChoiceService

_INSTALLED = False


def _choices():
    processed = DEFAULT_PROCESSED if DEFAULT_PROCESSED.exists() else LEGACY_PROCESSED
    return PotionChoiceService(processed).list_choices()


def _existing_named_choices(combo) -> list[str]:
    """Capture database-backed named/non-crafted potion choices already in the editor."""
    names: dict[str, str] = {}
    for index in range(combo.count()):
        text = str(combo.itemText(index) or "").strip()
        data = str(combo.itemData(index) or "").strip()
        value = data or text
        if not value:
            continue
        names.setdefault(value.casefold(), value)
    return sorted(names.values(), key=str.casefold)


def _configure_combo(combo) -> None:
    current_data = str(combo.currentData() or "").strip()
    current_text = str(combo.currentText() or "").strip()
    current = current_data or current_text
    named_choices = _existing_named_choices(combo)

    combo.blockSignals(True)
    combo.clear()
    combo.setEditable(False)
    combo.addItem("", "")

    for choice in _choices():
        combo.addItem(f"Crafted · {choice.label}", choice.canonical_id)
        index = combo.count() - 1
        combo.setItemData(
            index,
            f"Crafted potion effect family · {choice.formula_count} verified reagent formula(s)",
            Qt.ItemDataRole.ToolTipRole,
        )

    for name in named_choices:
        combo.addItem(f"Named · {name}", name)
        index = combo.count() - 1
        combo.setItemData(
            index,
            "Named/non-crafted potion from the canonical ESO entity catalog.",
            Qt.ItemDataRole.ToolTipRole,
        )

    if current:
        for index in range(combo.count()):
            if str(combo.itemData(index) or "").strip().casefold() == current.casefold():
                combo.setCurrentIndex(index)
                break
        else:
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
            "Choose either a canonical crafted-potion effect family or a named/non-crafted potion. "
            "Crafted entries group equivalent reagent recipes; selecting a potion does not imply uptime."
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
