from __future__ import annotations

from dataclasses import dataclass

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)


@dataclass(frozen=True)
class _Set:
    id: int
    name: str
    category: str | None
    max_equip_count: int | None


@dataclass(frozen=True)
class _Bonus:
    piece_count: int


class _Repository:
    def __init__(self, sets, bonuses):
        self._sets = tuple(sets)
        self._bonuses = dict(bonuses)

    def list_sets(self):
        return self._sets

    def get_bonuses(self, set_id):
        return list(self._bonuses.get(set_id, ()))


def test_standard_five_piece_set_exposes_only_actual_bonus_thresholds():
    repo = _Repository(
        (_Set(1, "Five Piece", "Trial", 5),),
        {1: (_Bonus(2), _Bonus(3), _Bonus(4), _Bonus(5))},
    )

    row = ExtremeGearSetBonusBreakpointService(repo).build().by_set_id(1)

    assert row is not None
    assert row.bonus_counts == (2, 3, 4, 5)
    assert 1 not in row.bonus_counts


def test_monster_and_mythic_thresholds_remain_literal():
    repo = _Repository(
        (
            _Set(2, "Monster", "Monster", 2),
            _Set(3, "Mythic", "Mythic", 1),
        ),
        {
            2: (_Bonus(1), _Bonus(2)),
            3: (_Bonus(1),),
        },
    )

    catalog = ExtremeGearSetBonusBreakpointService(repo).build()

    assert catalog.by_set_id(2).bonus_counts == (1, 2)
    assert catalog.by_set_id(3).bonus_counts == (1,)


def test_set_without_bonus_rows_is_not_a_distinct_set_effect_candidate():
    repo = _Repository((_Set(4, "No Bonus", "Other", 5),), {})

    catalog = ExtremeGearSetBonusBreakpointService(repo).build()

    assert catalog.by_set_id(4).bonus_counts == ()
    assert catalog.mechanically_relevant_sets == ()
    assert catalog.denominator_proven is True


def test_duplicate_bonus_rows_are_deduplicated_deterministically():
    repo = _Repository(
        (_Set(5, "Duplicate", "Trial", 5),),
        {5: (_Bonus(5), _Bonus(2), _Bonus(5), _Bonus(3))},
    )

    row = ExtremeGearSetBonusBreakpointService(repo).build().by_set_id(5)

    assert row.bonus_counts == (2, 3, 5)


def test_out_of_range_bonus_threshold_fails_closed():
    repo = _Repository(
        (_Set(6, "Broken", "Trial", 5),),
        {6: (_Bonus(2), _Bonus(6))},
    )

    catalog = ExtremeGearSetBonusBreakpointService(repo).build()
    row = catalog.by_set_id(6)

    assert row.bonus_counts == (2,)
    assert row.rejected_bonus_counts == (6,)
    assert catalog.denominator_proven is False
    assert any("Broken" in item and "outside canonical equip range" in item for item in catalog.unresolved)
