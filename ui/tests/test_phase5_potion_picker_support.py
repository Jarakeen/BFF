from pathlib import Path

from ui import phase5_potion_picker_support


def test_potion_picker_preserves_named_and_adds_crafted_sources() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "_existing_named_choices" in source
    assert 'combo.addItem(f"Crafted · {choice.label}", choice.canonical_id)' in source
    assert 'combo.addItem(f"Named · {name}", name)' in source
    assert "PotionChoiceService(processed).list_choices()" in source


def test_potion_picker_persists_stable_values_not_display_prefixes() -> None:
    source = Path(phase5_potion_picker_support.__file__).read_text(encoding="utf-8")

    assert "build.Potion = _persisted_value(self.potion)" in source
    assert "data = str(combo.currentData() or \"\").strip()" in source
    assert "return data or str(combo.currentText() or \"\").strip()" in source
