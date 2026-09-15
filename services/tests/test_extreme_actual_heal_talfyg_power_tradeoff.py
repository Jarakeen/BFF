from __future__ import annotations

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


_TALFYG = (
    "(5 items) Increases your Weapon and Spell Damage by 8-372. "
    "Increases your damage taken from Flame and Fighter's Guild abilities by 5%."
)


class _Repo:
    database_path = None

    def __init__(self) -> None:
        self._set = GearSet(1, "Talfyg's Treachery", "Test", 5)
        self._bonus = GearSetBonus(1, 1, 5, _TALFYG)

    def get_set(self, name):
        return self._set if name == self._set.name else None

    def get_set_by_id(self, set_id):
        return self._set if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return [self._bonus] if int(set_id) == 1 else []


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Talfyg's Treachery"
    return build


def test_talfyg_tradeoff_resolver_projects_only_reviewed_power_term() -> None:
    effects = ExtremeGearSetPowerTradeoffResolver().resolve(
        GearSetBonus(1, 1, 5, _TALFYG),
        source="Talfyg's Treachery (5)",
    )

    assert [(effect.stat.value, effect.value) for effect in effects] == [
        ("weapon_damage", 372.0),
        ("spell_damage", 372.0),
    ]
    assert all(effect.condition is None for effect in effects)


def test_talfyg_exact_unresolved_power_blocker_is_h1_reviewed() -> None:
    blocker = (
        "Talfyg's Treachery (5): active set bonus is not yet mechanic-mapped: "
        + _TALFYG
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Talfyg's Treachery",
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


def test_conditioned_extreme_gear_scoring_applies_talfyg_flat_power() -> None:
    inputs = ExtremeResourceConditionedGearStatInputResolver(_Repo()).resolve(
        _build(),
        condition_context=frozenset({"standing_still"}),
    )

    weapon = sum(item.value for item in inputs.core.weapon_damage.flat)
    spell = sum(item.value for item in inputs.core.spell_damage.flat)

    assert weapon == 372.0
    assert spell == 372.0
