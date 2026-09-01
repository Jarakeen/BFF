from __future__ import annotations

from types import SimpleNamespace

from ui.phase5_build_ui_support import _finish_endgame_gear


class _Combo:
    def __init__(self, value=""):
        self.value = value

    def setCurrentText(self, value):
        self.value = value


class _Slot:
    def __init__(self, is_empty):
        self.is_empty = is_empty


class _Row:
    def __init__(self, *, empty, quality="", level=""):
        self._slot = _Slot(empty)
        self.quality_combo = _Combo(quality)
        self.level_combo = _Combo(level)

    @property
    def value(self):
        return self._slot


def test_finish_endgame_gear_updates_only_populated_slots():
    equipped = _Row(empty=False, quality="Purple", level="CP150")
    blank = _Row(empty=True)
    editor = SimpleNamespace(gear_rows={"Head": equipped, "Waist": blank})

    _finish_endgame_gear(editor)

    assert equipped.quality_combo.value == "Gold"
    assert equipped.level_combo.value == "CP160"
    assert blank.quality_combo.value == ""
    assert blank.level_combo.value == ""
