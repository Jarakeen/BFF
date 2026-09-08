from __future__ import annotations

import pytest

from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def test_active_bar_legality_tracks_bar_swaps_in_plan_order() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(10.0, 1, RotationActionKind.SKILL, "Back Skill", "back"),
        RotationAction(15.0, 0, RotationActionKind.ULTIMATE, "Back Ultimate", "back"),
    )

    result = RotationActiveBarAssessor().assess(plan)

    assert result.legal
    assert result.initial_bar == "front"
    assert result.final_bar == "back"
    assert result.violations == ()


def test_active_bar_legality_rejects_wrong_bar_and_missing_bar() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.SKILL, "Wrong Bar Skill", "back"),
        RotationAction(8.0, 0, RotationActionKind.SKILL, "Barless Skill", None),
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, "Still Wrong", "front"),
    )

    result = RotationActiveBarAssessor().assess(plan)

    assert not result.legal
    assert [item.action_name for item in result.violations] == [
        "Wrong Bar Skill",
        "Barless Skill",
        "Still Wrong",
    ]
    assert result.violations[0].active_bar == "front"
    assert result.violations[0].scheduled_bar == "back"
    assert result.violations[1].scheduled_bar is None
    assert result.violations[2].active_bar == "back"
    assert result.violations[2].scheduled_bar == "front"


def test_active_bar_legality_audits_light_and_heavy_attacks() -> None:
    plan = _plan(
        RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
        RotationAction(4.0, 0, RotationActionKind.HEAVY_ATTACK, bar="back"),
        RotationAction(6.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(6.0, 1, RotationActionKind.LIGHT_ATTACK, bar="back"),
        RotationAction(8.0, 0, RotationActionKind.HEAVY_ATTACK),
    )

    result = RotationActiveBarAssessor().assess(plan)

    assert not result.legal
    assert [(item.action_kind, item.scheduled_bar, item.active_bar) for item in result.violations] == [
        (RotationActionKind.HEAVY_ATTACK, "back", "front"),
        (RotationActionKind.HEAVY_ATTACK, None, "back"),
    ]
    assert result.violations[0].action_name == "heavy_attack"
    assert result.violations[1].reason == "bar-bound action does not declare its scheduled bar"


def test_same_timestamp_swap_order_applies_to_weapon_attacks() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
        RotationAction(10.0, 1, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(10.0, 2, RotationActionKind.HEAVY_ATTACK, bar="back"),
    )

    result = RotationActiveBarAssessor().assess(plan)

    assert result.legal
    assert result.final_bar == "back"


def test_active_bar_legality_supports_explicit_back_bar_start_and_rejects_invalid_start() -> None:
    plan = _plan(
        RotationAction(2.0, 0, RotationActionKind.SKILL, "Back Opener", "back"),
    )

    result = RotationActiveBarAssessor().assess(plan, initial_bar="back")

    assert result.legal
    assert result.initial_bar == "back"
    assert result.final_bar == "back"

    with pytest.raises(ValueError, match="initial bar must be front or back"):
        RotationActiveBarAssessor().assess(plan, initial_bar="middle")
