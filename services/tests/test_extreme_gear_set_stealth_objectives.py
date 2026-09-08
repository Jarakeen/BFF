from __future__ import annotations

import pytest

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, gear_set: GearSet, bonuses: tuple[GearSetBonus, ...]):
        self._set = gear_set
        self._bonuses = bonuses

    def list_sets(self):
        return (self._set,)

    def get_set(self, name):
        return self._set if name == self._set.name else None

    def get_bonuses(self, set_id):
        return list(self._bonuses if int(set_id) == self._set.id else ())


def _night_terror_repo() -> _Repo:
    gear_set = GearSet(1, "Night Terror", "standard", 5)
    bonuses = (
        GearSetBonus(
            id=1,
            set_id=1,
            piece_count=3,
            description=(
                "(3 items) Reduces the radius you can be detected while Sneaking by 2 meters. "
                "Reduces the cost of Sneak by 0-10%."
            ),
        ),
    )
    return _Repo(gear_set, bonuses)


def test_night_terror_projects_detection_radius_reduction_as_meters():
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _night_terror_repo(),
        "Night Terror",
        "detection_radius_reduction",
        equipped_piece_count=3,
    )

    assert row.reviewed_delta == 2.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_night_terror_projects_sneak_cost_reduction_as_ratio():
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _night_terror_repo(),
        "Night Terror",
        "sneak_cost_reduction",
        equipped_piece_count=3,
    )

    assert row.reviewed_delta == pytest.approx(0.10)
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_stealth_objectives_are_first_class_reviewed_gear_set_objectives():
    assert "detection_radius_reduction" in ExtremeGearSetObjectiveService.REVIEWED_OBJECTIVES
    assert "sneak_cost_reduction" in ExtremeGearSetObjectiveService.REVIEWED_OBJECTIVES
