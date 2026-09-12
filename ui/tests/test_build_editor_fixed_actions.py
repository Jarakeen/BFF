from pathlib import Path

from ui import character_creation_easy_mode_support


def _source() -> str:
    return Path(character_creation_easy_mode_support.__file__).read_text(encoding="utf-8")


def test_build_save_and_cancel_live_in_fixed_page_action_bar() -> None:
    source = _source()

    assert 'FoundryButton(\n            "Cancel", role=ButtonRole.SECONDARY, compact=True' in source
    assert 'FoundryButton(\n            "Save Build", role=ButtonRole.PRIMARY, compact=True' in source
    assert "self.cancel_build_button.clicked.connect(lambda *_: self._cancel_edit_tab())" in source
    assert "self.save_build_button.clicked.connect(lambda *_: self._save_edit_tab())" in source
    assert "action_layout.insertWidget(delete_index, self.cancel_build_button)" in source
    assert "action_layout.insertWidget(delete_index + 1, self.save_build_button)" in source


def test_boss_alternates_keeps_only_contextual_add_action() -> None:
    source = _source()

    assert "for button in (add_build, save, cancel):" in source
    assert "button.deleteLater()" in source
    boss_section = source.split("def _boss_card(self):", 1)[1].split("def _save_edit_tab", 1)[0]
    assert "row.addWidget(add_boss)" in boss_section
    assert "row.addWidget(save)" not in boss_section
    assert "row.addWidget(cancel)" not in boss_section


def test_finish_endgame_gear_sets_truly_superb_enchantment_tier() -> None:
    source = _source()

    assert "original_finish_endgame_gear(self)" in source
    assert 'row.enchant_tier_combo.setCurrentText("Truly Superb")' in source
    assert "phase5_build_ui_support._finish_endgame_gear = _finish_endgame_gear" in source
