from __future__ import annotations

import pytest

from minmax.gear_sets import GearSet, GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_gear_set_power_tradeoff_resolver import (
    ExtremeGearSetPowerTradeoffResolver,
)
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)


_DREUGH = (
    "(5 items) Gain Major Brutality and Sorcery at all times, increasing your Weapon and Spell Damage by 20%. "
    "When you kill an enemy, you gain Major Expedition for 8 seconds, increasing your Movement Speedby 30%."
)


class _Repo:
    database_path = None

    def __init__(self) -> None:
        self._set = GearSet(1, "Dreugh King Slayer", "Test", 5)
        self._bonus = GearSetBonus(1, 1, 5, _DREUGH)

    def get_set(self, name):
        return self._set if name == self._set.name else None

    def get_set_by_id(self, set_id):
        return self._set if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return [self._bonus] if int(set_id) == 1 else []


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Dreugh King Slayer"
    return build


def test_dreugh_tradeoff_resolver_projects_major_power_only() -> None:
    effects = ExtremeGearSetPowerTradeoffResolver().resolve(
        GearSetBonus(1, 1, 5, _DREUGH),
        source="Dreugh King Slayer (5)",
    )

    assert [(effect.stat.value, effect.operation.value, effect.value) for effect in effects] == [
        ("weapon_damage", "add_percent", 20.0),
        ("spell_damage", "add_percent", 20.0),
    ]
    assert all(effect.condition is None for effect in effects)


def test_dreugh_exact_unresolved_power_blocker_is_h1_reviewed() -> None:
    blocker = "Dreugh King Slayer (5): active set bonus is not yet mechanic-mapped: " + _DREUGH
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Dreugh King Slayer",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)


def test_conditioned_extreme_gear_scoring_applies_dreugh_major_power() -> None:
    inputs = ExtremeResourceConditionedGearStatInputResolver(_Repo()).resolve(
        _build(),
        condition_context=frozenset({"standing_still"}),
    )

    weapon = sum(item.value for item in inputs.core.weapon_damage.percent)
    spell = sum(item.value for item in inputs.core.spell_damage.percent)

    assert weapon == pytest.approx(0.20)
    assert spell == pytest.approx(0.20)
