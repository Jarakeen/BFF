from pathlib import Path

from ui import phase5_potion_picker_support


def test_potion_picker_preserves_named_and_adds_crafted_sources() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "_existing_named_choices" in source
    assert 'combo.addItem(f"Crafted · {choice.label}", choice.canonical_id)' in source
    assert 'combo.addItem(f"Named · {name}", name)' in source
    assert "PotionChoiceService(processed).list_choices()" in source


def test_potion_picker_uses_current_canonical_alchemy_source_with_legacy_fallback() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "DEFAULT_PROCESSED" in source
    assert "LEGACY_PROCESSED" in source
    assert "DEFAULT_PROCESSED if DEFAULT_PROCESSED.exists() else LEGACY_PROCESSED" in source


def test_build_editor_dropdowns_share_searchable_combo_behavior() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "_configure_all_build_dropdowns" in source
    assert "editor.findChildren(QComboBox)" in source
    assert "combo.setEditable(True)" in source
    assert "QCompleter(combo.model(), combo)" in source
    assert "CaseInsensitive" in source
    assert "MatchContains" in source
    assert "PopupCompletion" in source
    assert "setClearButtonEnabled(True)" in source
    assert "NoInsert" in source
    assert "BuildEditor.__init__ = init_with_searchable_dropdowns" in source


def test_newly_searchable_fixed_catalogs_reject_unfinished_typed_values() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "enforce_catalog=not was_editable" in source
    assert "foundryLastValidIndex" in source
    assert "editingFinished.connect(restore_catalog_choice)" in source
    assert "_exact_text_index(combo, text)" in source


def test_potion_picker_persists_selected_data_or_new_typed_text() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "build.Potion = _persisted_value(self.potion)" in source
    assert "text = str(combo.currentText() or \"\").strip()" in source
    assert "text == str(combo.itemText(index) or \"\").strip()" in source
    assert "data = str(combo.itemData(index) or \"\").strip()" in source
    assert "return text" in source
