from __future__ import annotations

import pytest

from minmax.champion_point_movement_effects import ChampionPointMovementEffectResolver
from minmax.champion_point_static_repository import ChampionPointRecord
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


class _Repository:
    def __init__(self, record: ChampionPointRecord | None) -> None:
        self.record = record

    def get(self, _name: str):
        return self.record

    @staticmethod
    def _stages(record: ChampionPointRecord, points: int) -> int:
        allocated = max(0, min(int(points), record.max_points or int(points)))
        thresholds = tuple(value for value in record.jump_points if value > 0)
        if thresholds:
            return sum(1 for value in thresholds if allocated >= value)
        return allocated


def test_celerity_projects_movement_speed_from_tooltip_stages() -> None:
    record = ChampionPointRecord(
        name="Celerity",
        skill_type=1,
        max_points=50,
        jump_points=(10, 20, 30, 40, 50),
        description="Increases your Movement Speed by 2% per stage.",
    )
    effects, unresolved = ChampionPointMovementEffectResolver(_Repository(record)).resolve(
        "Celerity", 50
    )

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.MOVEMENT_SPEED
    assert effects[0].operation is EffectOperation.ADD_PERCENT
    assert effects[0].unit is EffectUnit.PERCENT
    assert effects[0].value == pytest.approx(10.0)


def test_wind_chaser_projects_sprint_only_speed() -> None:
    record = ChampionPointRecord(
        name="Wind Chaser",
        skill_type=1,
        max_points=16,
        jump_points=(8, 16),
        description="Increases your Movement Speed when Sprinting by 2% per stage.",
    )
    effects, unresolved = ChampionPointMovementEffectResolver(_Repository(record)).resolve(
        "Wind Chaser", 16
    )

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.SPRINT_SPEED
    assert effects[0].value == pytest.approx(4.0)


def test_unmapped_movement_cp_fails_closed() -> None:
    record = ChampionPointRecord(
        name="Mystery Runner",
        skill_type=1,
        max_points=10,
        jump_points=(10,),
        description="Runs mysteriously faster.",
    )
    effects, unresolved = ChampionPointMovementEffectResolver(_Repository(record)).resolve(
        "Mystery Runner", 10
    )

    assert effects == []
    assert unresolved == ["Champion Point movement effect not mapped: Mystery Runner"]
