from __future__ import annotations

from types import SimpleNamespace

from ui.character_progression_compact_cards_support import (
    _buy_all_passive_cp,
    _buy_all_skill_progression,
)


class _Check:
    def __init__(self, checked: bool = False):
        self.checked = checked

    def setChecked(self, checked: bool) -> None:
        self.checked = checked


class _Spin:
    def __init__(self, maximum: int, value: int = -1):
        self._maximum = maximum
        self.value = value

    def maximum(self) -> int:
        return self._maximum

    def setValue(self, value: int) -> None:
        self.value = value


def test_buy_all_skill_progression_unlocks_every_line_and_maxes_every_passive():
    first_check = _Check()
    second_check = _Check()
    first_spin = _Spin(2)
    second_spin = _Spin(4, value=1)
    dialog = SimpleNamespace(
        _line_checks={"Blacksmithing": first_check, "Undaunted": second_check},
        _passive_spins={
            "metalworking": ("Metalworking", first_spin),
            "undaunted mettle": ("Undaunted Mettle", second_spin),
        },
    )

    _buy_all_skill_progression(dialog)

    assert first_check.checked is True
    assert second_check.checked is True
    assert first_spin.value == 2
    assert second_spin.value == 4


def test_buy_all_passive_cp_maxes_every_passive_champion_star():
    first_spin = _Spin(50)
    second_spin = _Spin(20, value=3)
    dialog = SimpleNamespace(
        _cp_spins={
            "tireless discipline": ("Tireless Discipline", first_spin),
            "quick recovery": ("Quick Recovery", second_spin),
        }
    )

    _buy_all_passive_cp(dialog)

    assert first_spin.value == 50
    assert second_spin.value == 20
