from dataclasses import dataclass

from minmax.effects import Effect, EffectOperation
from minmax.gear_set_activation_rules import (
    TORC_OF_THE_LAST_AYLEID_KING,
    active_item_set_bonus_counts,
)
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class _Set:
    id: int
    name: str


@dataclass(frozen=True)
class _Bonus:
    piece_count: int


class _Repository:
    def __init__(self):
        self.rows = {
            TORC_OF_THE_LAST_AYLEID_KING: _Set(1, TORC_OF_THE_LAST_AYLEID_KING),
            "Ordinary Five": _Set(2, "Ordinary Five"),
        }

    def get_set(self, name):
        return self.rows.get(str(name))

    def get_set_by_id(self, set_id):
        for row in self.rows.values():
            if row.id == set_id:
                return row
        return None

    def get_bonuses(self, set_id):
        if set_id == 1:
            return [_Bonus(1)]
        if set_id == 2:
            return [_Bonus(2), _Bonus(5)]
        return []


class _Resolver:
    def resolve(self, bonus, *, use_max_value=True, source=""):
        return [
            Effect(
                operation=EffectOperation.ADD,
                value=float(bonus.piece_count),
                source=source,
                stat=StatId.MAX_MAGICKA,
            )
        ]


def test_without_torc_all_equipped_set_bonus_counts_remain_active():
    counts = active_item_set_bonus_counts({"Ordinary Five": 5})

    assert counts == {"Ordinary Five": 5}


def test_torc_suppresses_every_other_item_set_bonus_count_only():
    equipped = {
        TORC_OF_THE_LAST_AYLEID_KING: 1,
        "Ordinary Five": 5,
    }

    active = active_item_set_bonus_counts(equipped)

    assert active == {TORC_OF_THE_LAST_AYLEID_KING: 1}
    assert equipped["Ordinary Five"] == 5


def test_gear_set_effect_service_resolves_torc_but_not_suppressed_set_effects():
    service = GearSetEffectService(_Repository(), resolver=_Resolver())

    effects = service.active_static_effects(
        {
            TORC_OF_THE_LAST_AYLEID_KING: 1,
            "Ordinary Five": 5,
        }
    )

    assert [effect.source for effect in effects] == [
        f"{TORC_OF_THE_LAST_AYLEID_KING} (1)"
    ]
    assert [effect.value for effect in effects] == [1.0]


def test_ordinary_set_effect_resolution_is_unchanged_without_torc():
    service = GearSetEffectService(_Repository(), resolver=_Resolver())

    effects = service.active_static_effects({"Ordinary Five": 5})

    assert [effect.source for effect in effects] == [
        "Ordinary Five (2)",
        "Ordinary Five (5)",
    ]
