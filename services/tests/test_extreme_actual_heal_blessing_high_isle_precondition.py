from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.gear_sets import GearSet, GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    BLESSING_OF_HIGH_ISLE_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)


_BLESSING = (
    "(5 items) When you are healed while in combat, increase your Weapon and Spell Damage by 8-369 for 5 seconds."
)


class _Repo:
    database_path = None

    def __init__(self) -> None:
        self._set = GearSet(1, "Blessing of High Isle", "Test", 5)
        self._bonus = GearSetBonus(1, 1, 5, _BLESSING)

    def get_set(self, name):
        return self._set if name == self._set.name else None

    def get_set_by_id(self, set_id):
        return self._set if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return [self._bonus] if int(set_id) == 1 else []


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Blessing of High Isle"
    return build


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity(id INTEGER PRIMARY KEY, entity_type TEXT, name TEXT)"
        )
    return path


def test_blessing_effect_requires_explicit_recent_heal_condition() -> None:
    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(
        GearSetBonus(1, 1, 5, _BLESSING),
        source="Blessing of High Isle (5)",
    )

    assert [(effect.stat.value, effect.value, effect.condition) for effect in effects] == [
        ("weapon_damage", 369.0, BLESSING_OF_HIGH_ISLE_CONDITION),
        ("spell_damage", 369.0, BLESSING_OF_HIGH_ISLE_CONDITION),
    ]


def test_blessing_witness_is_constructed_only_when_five_piece_is_equipped(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(_database(tmp_path))

    active = service.resolve(_build())
    absent = service.resolve(PlayerBuild())

    assert BLESSING_OF_HIGH_ISLE_CONDITION in active.condition_context
    assert any("Blessing of High Isle" in item for item in active.evidence)
    assert BLESSING_OF_HIGH_ISLE_CONDITION not in absent.condition_context


def test_conditioned_scoring_applies_blessing_only_with_runtime_witness() -> None:
    resolver = ExtremeResourceConditionedGearStatInputResolver(_Repo())

    inactive = resolver.resolve(_build(), condition_context=frozenset({"standing_still"}))
    active = resolver.resolve(
        _build(),
        condition_context=frozenset({"standing_still", BLESSING_OF_HIGH_ISLE_CONDITION}),
    )

    inactive_weapon = sum(item.value for item in inactive.core.weapon_damage.flat)
    inactive_spell = sum(item.value for item in inactive.core.spell_damage.flat)
    active_weapon = sum(item.value for item in active.core.weapon_damage.flat)
    active_spell = sum(item.value for item in active.core.spell_damage.flat)

    assert inactive_weapon == 0.0
    assert inactive_spell == 0.0
    assert active_weapon == 369.0
    assert active_spell == 369.0


def test_blessing_unresolved_power_blocker_is_h1_reviewed() -> None:
    blocker = (
        "Blessing of High Isle (5): active set bonus is not yet mechanic-mapped: "
        + _BLESSING
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Blessing of High Isle",
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
