from __future__ import annotations

from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)


class _Set:
    id = 1
    name = "Green Pact"


class _Bonus:
    id = 1
    set_id = 1
    piece_count = 5
    description = (
        "(5 items) While you have a food buff active, your Max Health is increased by "
        "58-2500 and Health Recovery by 8-356."
    )


class _Repository:
    database_path = None

    def get_set(self, name):
        return _Set() if name == "Green Pact" else None

    def get_set_by_id(self, set_id):
        return _Set() if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return [_Bonus()] if int(set_id) == 1 else []


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Green Pact"
    return build


def test_food_condition_controls_reviewed_resource_set_effects() -> None:
    resolver = ExtremeResourceConditionedGearStatInputResolver(_Repository())

    inactive = resolver.resolve(_build(), condition_context=frozenset())
    active = resolver.resolve(
        _build(), condition_context=frozenset({"food_buff_active"})
    )

    assert inactive.health.set_flat == 0.0
    assert inactive.health_recovery.set_flat == 0.0
    assert active.health.set_flat == 2500.0
    assert active.health_recovery.set_flat == 356.0
