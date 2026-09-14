from pathlib import Path

from ui import build_editor_performance


def test_build_editor_reuses_one_persistent_widget() -> None:
    source = Path(build_editor_performance.__file__).read_text(encoding="utf-8")

    assert "_persistent_build_editor" in source
    assert "editor = self._editor(build)" in source
    assert "self._persistent_build_editor = editor" in source
    assert "editor.load(build)" in source


def test_performance_layer_does_not_monkeypatch_skill_bar_logic() -> None:
    source = Path(build_editor_performance.__file__).read_text(encoding="utf-8")

    assert "EligibleSkillBarRow.set_class =" not in source
    assert "EligibleSkillBarRow.set_affiliation =" not in source
    assert "EligibleSkillBarRow.set_form =" not in source
    assert "eligible._icon_for_skill =" not in source
    assert "lru_cache" not in source


def test_finish_endgame_gear_is_batched_without_signal_or_repaint_storms() -> None:
    source = Path(build_editor_performance.__file__).read_text(encoding="utf-8")

    assert "def finish_endgame_gear_batched" in source
    assert "QSignalBlocker" in source
    assert "editor.setUpdatesEnabled(False)" in source
    assert 'row.quality_combo.setCurrentText("Gold")' in source
    assert 'row.level_combo.setCurrentText("CP160")' in source
    assert 'row.enchant_tier_combo.setCurrentText("Truly Superb")' in source
    assert 'combo.setProperty("foundryLastValidIndex", combo.currentIndex())' in source
    assert "phase5_build_ui_support._finish_endgame_gear = finish_endgame_gear_batched" in source
