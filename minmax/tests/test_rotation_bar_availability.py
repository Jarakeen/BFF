from __future__ import annotations

import pytest

from minmax.rotation_bar_availability import (
    RotationBarAvailabilityAssessor,
    RotationBarAvailabilityWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=tuple(actions),
    )


def test_single_bar_window_allows_actions_only_on_available_bar() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(5.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(7.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
    )
    window = RotationBarAvailabilityWindow(
        name="single-bar mechanic",
        start_seconds=4.0,
        end_seconds=8.0,
        allowed_bars=frozenset({"front"}),
        bar_swaps_allowed=False,
    )

    result = RotationBarAvailabilityAssessor().assess(plan, (window,))

    assert result.legal is True
    assert result.violations == ()


def test_single_bar_window_rejects_other_bar_action_and_swap() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(5.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
        RotationAction(6.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
    )
    window = RotationBarAvailabilityWindow(
        name="single-bar mechanic",
        start_seconds=4.0,
        end_seconds=8.0,
        allowed_bars=frozenset({"front"}),
        bar_swaps_allowed=False,
    )

    result = RotationBarAvailabilityAssessor().assess(plan, (window,))

    assert result.legal is False
    assert [item.reason for item in result.violations] == [
        "scheduled action uses an unavailable bar",
        "bar swapping is forbidden during restriction",
    ]


def test_restriction_detects_illegal_active_bar_at_window_entry() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
        RotationAction(6.0, 0, RotationActionKind.WAIT, bar="back"),
    )
    window = RotationBarAvailabilityWindow(
        name="front-only mechanic",
        start_seconds=5.0,
        end_seconds=8.0,
        allowed_bars=frozenset({"front"}),
        bar_swaps_allowed=False,
    )

    result = RotationBarAvailabilityAssessor().assess(plan, (window,))

    assert result.legal is False
    assert result.violations[0].time_seconds == 5.0
    assert result.violations[0].action_kind is None
    assert result.violations[0].action_bar == "back"
    assert result.violations[0].reason == "active bar at restriction entry is not available"


def test_window_can_allow_swapping_between_both_bars() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
    )
    window = RotationBarAvailabilityWindow(
        name="normal access",
        start_seconds=4.0,
        end_seconds=8.0,
        allowed_bars=frozenset({"front", "back"}),
        bar_swaps_allowed=True,
    )

    assert RotationBarAvailabilityAssessor().assess(plan, (window,)).legal is True


def test_overlapping_bar_state_windows_fail_explicitly() -> None:
    plan = _plan()
    windows = (
        RotationBarAvailabilityWindow("one", 2.0, 6.0, frozenset({"front"})),
        RotationBarAvailabilityWindow("two", 5.0, 8.0, frozenset({"back"})),
    )

    with pytest.raises(ValueError, match="cannot overlap"):
        RotationBarAvailabilityAssessor().assess(plan, windows)
