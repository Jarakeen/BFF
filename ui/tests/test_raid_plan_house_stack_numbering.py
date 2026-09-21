from __future__ import annotations

from ui.raid_plan_page import HOUSE_STACK_ROWS, RAID_PLAN_SEATS


def test_raid_plan_house_stack_numbering_is_top_5_to_8_bottom_1_to_4() -> None:
    assert HOUSE_STACK_ROWS == (
        ("DD 5", "DD 6", "DD 7", "DD 8"),
        ("DD 1", "DD 2", "DD 3", "DD 4"),
    )


def test_house_stack_seats_remain_canonical_raid_plan_chairs() -> None:
    flattened = tuple(seat for row in HOUSE_STACK_ROWS for seat in row)
    assert set(flattened) == {f"DD {number}" for number in range(1, 9)}
    assert set(flattened).issubset(set(RAID_PLAN_SEATS))
