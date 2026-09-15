from pathlib import Path

from ui import character_creation_easy_mode_support, phase5_build_ui_support


def _easy_mode_source() -> str:
    return Path(character_creation_easy_mode_support.__file__).read_text(encoding="utf-8")


def _phase5_source() -> str:
    return Path(phase5_build_ui_support.__file__).read_text(encoding="utf-8")


def test_build_save_and_cancel_live_in_fixed_page_action_bar() -> None:
    source = _easy_mode_source()

    assert 'FoundryButton(\n            "Cancel", role=ButtonRole.SECONDARY, compact=True' in source
    assert 'FoundryButton(\n            "Save Build", role=ButtonRole.PRIMARY, compact=True' in source
    assert "self.cancel_build_button.clicked.connect(lambda *_: self._cancel_edit_tab())" in source
    assert "self.save_build_button.clicked.connect(lambda *_: self._save_edit_tab())" in source
    assert "action_layout.insertWidget(delete_index, self.cancel_build_button)" in source
    assert "action_layout.insertWidget(delete_index + 1, self.save_build_button)" in source


def test_boss_alternates_keeps_only_contextual_add_action() -> None:
    source = _easy_mode_source()

    assert "for button in (add_build, save, cancel):" in source
    assert "button.deleteLater()" in source
    boss_section = source.split("def _boss_card(self):", 1)[1].split("def _save_edit_tab", 1)[0]
    assert "row.addWidget(add_boss)" in boss_section
    assert "row.addWidget(save)" not in boss_section
    assert "row.addWidget(cancel)" not in boss_section


def test_phase5_owns_complete_finish_endgame_gear_action() -> None:
    phase5 = _phase5_source()
    easy_mode = _easy_mode_source()

    assert 'row.quality_combo.setCurrentText("Gold")' in phase5
    assert 'row.level_combo.setCurrentText("CP160")' in phase5
    assert 'row.enchant_tier_combo.setCurrentText("Truly Superb")' in phase5
    assert "BuildEditor.finish_endgame_gear = _finish_endgame_gear" in phase5

    assert "BuildEditor.finish_endgame_gear =" not in easy_mode
    assert "original_finish_endgame_gear" not in easy_mode
    assert "phase5_build_ui_support._finish_endgame_gear =" not in easy_mode
