from pathlib import Path

from ui import build_editor_performance


def test_build_editor_reuses_one_persistent_widget() -> None:
    source = Path(build_editor_performance.__file__).read_text(encoding="utf-8")

    assert "_persistent_build_editor" in source
    assert "editor = self._editor(build)" in source
    assert "self._persistent_build_editor = editor" in source
    assert "editor.load(build)" in source


def test_skill_rebuilds_are_deduplicated_and_icons_cached() -> None:
    source = Path(build_editor_performance.__file__).read_text(encoding="utf-8")

    assert "if self._selected_class == value:" in source
    assert "if self.vampire == vampire and self.werewolf == werewolf:" in source
    assert "lru_cache(maxsize=4096)" in source
