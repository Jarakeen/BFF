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
