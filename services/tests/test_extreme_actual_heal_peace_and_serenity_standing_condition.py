from __future__ import annotations

from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)


class _Set:
    id = 1
    name = "Peace and Serenity"


class _Bonus:
    id = 1
    set_id = 1
    piece_count = 5
    description = (
        "(5 items) While you are standing still, you gain 10-465 Weapon and Spell Damage. "
        "While you are moving, you gain 4-203 Health, Magicka, and Stamina Recovery."
    )


class _Repository:
    database_path = None

    def get_set(self, name):
        return _Set() if name == "Peace and Serenity" else None

    def get_set_by_id(self, set_id):
        return _Set() if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return [_Bonus()] if int(set_id) == 1 else []


def _build() -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Peace and Serenity"
    return build


def _core_value(inputs, stat: StatId) -> float:
    field = "spell_damage" if stat is StatId.SPELL_DAMAGE else "weapon_damage"
    trace = getattr(inputs.core, field)
    return sum(item.value for item in trace.additive_after_percent)


def test_standing_condition_controls_peace_and_serenity_power() -> None:
    resolver = ExtremeResourceConditionedGearStatInputResolver(_Repository())

    inactive = resolver.resolve(_build(), condition_context=frozenset())
    standing = resolver.resolve(
        _build(), condition_context=frozenset({"standing_still"})
    )

    assert _core_value(inactive, StatId.WEAPON_DAMAGE) == 0.0
    assert _core_value(inactive, StatId.SPELL_DAMAGE) == 0.0
    assert _core_value(standing, StatId.WEAPON_DAMAGE) == 465.0
    assert _core_value(standing, StatId.SPELL_DAMAGE) == 465.0
