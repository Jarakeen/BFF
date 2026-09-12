from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter

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


def _exact_text_index(combo: QComboBox, text: str) -> int:
    wanted = str(text or "").strip().casefold()
    for index in range(combo.count()):
        if str(combo.itemText(index) or "").strip().casefold() == wanted:
            return index
    return -1


def _configure_search(combo: QComboBox, *, enforce_catalog: bool = False) -> None:
    """Give a combo the standard Build Editor type-to-filter behavior.

    Existing editable selectors keep their historical free-text behavior. Fixed
    catalog selectors become editable for searching, but an unfinished or unknown
    value is restored to the last real catalog choice when editing finishes.
    """
    if bool(combo.property("foundrySearchConfigured")):
        return

    last_valid_index = combo.currentIndex()
    combo.setProperty("foundryLastValidIndex", last_valid_index)
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.setDuplicatesEnabled(False)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)

    line_edit = combo.lineEdit()
    if line_edit is not None:
        line_edit.setClearButtonEnabled(True)

    if enforce_catalog and line_edit is not None:
        def remember_valid(index: int) -> None:
            if index >= 0:
                combo.setProperty("foundryLastValidIndex", index)

        def restore_catalog_choice() -> None:
            text = str(combo.currentText() or "").strip()
            exact = _exact_text_index(combo, text)
            if exact >= 0:
                combo.setCurrentIndex(exact)
                combo.setProperty("foundryLastValidIndex", exact)
                return
            if not text:
                blank = _exact_text_index(combo, "")
                combo.setCurrentIndex(blank if blank >= 0 else -1)
                return
            try:
                fallback = int(combo.property("foundryLastValidIndex"))
            except (TypeError, ValueError):
                fallback = -1
            combo.setCurrentIndex(fallback if 0 <= fallback < combo.count() else 0)

        combo.currentIndexChanged.connect(remember_valid)
        line_edit.editingFinished.connect(restore_catalog_choice)

    combo.setProperty("foundrySearchConfigured", True)


def _configure_all_build_dropdowns(editor) -> None:
    """Apply one searchable-combo interaction to every Build Editor dropdown."""
    for combo in editor.findChildren(QComboBox):
        was_editable = combo.isEditable()
        _configure_search(combo, enforce_catalog=not was_editable)


def _configure_combo(combo) -> None:
    current_data = str(combo.currentData() or "").strip()
    current_text = str(combo.currentText() or "").strip()
    current = current_data or current_text
    named_choices = _existing_named_choices(combo)

    combo.blockSignals(True)
    combo.clear()
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
    _configure_search(combo)
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
    text = str(combo.currentText() or "").strip()
    index = combo.currentIndex()
    if index >= 0 and text == str(combo.itemText(index) or "").strip():
        data = str(combo.itemData(index) or "").strip()
        if data:
            return data
    return text


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.build_editor import BuildEditor

    original_init = BuildEditor.__init__
    original_skills_card = BuildEditor._build_skills_card
    original_load = BuildEditor.load
    original_model = BuildEditor.model

    def init_with_searchable_dropdowns(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        _configure_all_build_dropdowns(self)

    def skills_card_with_canonical_potions(self):
        card = original_skills_card(self)
        _configure_combo(self.potion)
        self.potion.setToolTip(
            "Choose either a canonical crafted-potion effect family or a named/non-crafted potion. "
            "Type any part of the potion name or effect to filter the list. "
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

    BuildEditor.__init__ = init_with_searchable_dropdowns
    BuildEditor._build_skills_card = skills_card_with_canonical_potions
    BuildEditor.load = load_with_canonical_potions
    BuildEditor.model = property(model_with_canonical_potions)

    _INSTALLED = True
