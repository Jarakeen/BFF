from __future__ import annotations

import pytest

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self) -> None:
        self._set = GearSet(1, "Archer's Mind", "Test", 5)
        self._bonus = GearSetBonus(
            id=1,
            set_id=1,
            piece_count=5,
            description=(
                "Increases your Critical Damage and Healing by 8%. "
                "Increases your Critical Damage and Healing by an additional 16% "
                "when you are Sneaking or Invisible."
            ),
        )

    def get_set(self, name):
        return self._set if name == self._set.name else None

    def get_bonuses(self, set_id):
        return [self._bonus] if int(set_id) == self._set.id else []


def test_archers_mind_keeps_unconditional_critical_healing_and_suppresses_standing_inactive_bonus() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo(),
        "Archer's Mind",
        "critical_healing",
    )

    assert row.mechanic_complete is True
    assert row.unresolved == ()
    assert row.reviewed_delta == pytest.approx(0.08)
    assert any(
        effect.condition == "sneaking_or_invisible"
        for effect in row.source_effects
    )


def test_archers_mind_critical_damage_path_remains_fail_closed_for_non_h1_objective() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo(),
        "Archer's Mind",
        "critical_damage",
    )

    assert row.reviewed_delta == pytest.approx(0.08)
    assert row.mechanic_complete is False
    assert any("sneaking_or_invisible" in item for item in row.unresolved)
