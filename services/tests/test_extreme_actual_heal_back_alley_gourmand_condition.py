from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)


class _Repository:
    database_path = None

    def __init__(self) -> None:
        self.gear_set = GearSet(1, "Back-Alley Gourmand", "Overland", 5)
        self.bonuses = [
            GearSetBonus(1, 1, 2, "(2 items) Adds 657 Critical Chance"),
            GearSetBonus(2, 1, 3, "(3 items) Adds 657 Critical Chance"),
            GearSetBonus(3, 1, 4, "(4 items) Adds 129 Weapon and Spell Damage"),
            GearSetBonus(
                4,
                1,
                5,
                "(5 items) While you have a food buff active, your Critical Damage "
                "and Critical Healing is increased by 13%.",
            ),
        ]

    def get_set(self, name):
        return self.gear_set if name == self.gear_set.name else None

    def get_set_by_id(self, set_id):
        return self.gear_set if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return list(self.bonuses) if int(set_id) == 1 else []

    def list_sets(self):
        return (self.gear_set,)


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Back-Alley Gourmand"
    return build


def test_objective_service_records_food_conditioned_critical_healing() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repository(),
        "Back-Alley Gourmand",
        "critical_healing",
    )

    assert row.mechanic_complete is True
    assert row.reviewed_delta == 0.13
    assert any(
        effect.stat is StatId.CRITICAL_HEALING
        and effect.condition == "food_buff_active"
        and effect.value == 13.0
        for effect in row.source_effects
    )


def test_conditioned_scorer_activates_bonus_only_with_food_evidence() -> None:
    resolver = ExtremeResourceConditionedGearStatInputResolver(_Repository())

    inactive = resolver.resolve(_build(), condition_context=frozenset())
    active = resolver.resolve(
        _build(),
        condition_context=frozenset({"food_buff_active"}),
    )

    inactive_trace = inactive.core.critical_healing
    active_trace = active.core.critical_healing
    assert sum(item.value for item in inactive_trace.additive_after_percent) == 0.0
    assert sum(item.value for item in active_trace.additive_after_percent) == 0.13
