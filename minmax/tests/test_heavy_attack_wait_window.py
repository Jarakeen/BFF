from minmax.heavy_attack_wait_window import derive_heavy_attack_decision_window
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecisionContext


def _context(*, next_decision=3.0, next_due=(), plan_end=10.0):
    slot = RotationAction(2.0, 1, RotationActionKind.SKILL, "Long Buff", "front")
    return PrematureRecastDecisionContext(
        time_seconds=2.0,
        bar="front",
        candidate=slot,
        slot=slot,
        next_due=tuple(next_due),
        rules=(RotationRecastRule("Long Buff", 10.0, bar="front"),),
        next_decision_time_seconds=next_decision,
        plan_end_seconds=plan_end,
    )


def test_one_second_gap_rejects_longer_heavy_window() -> None:
    window = derive_heavy_attack_decision_window(
        context=_context(next_decision=3.0),
        required_window_seconds=1.8,
    )

    assert window.available_window_seconds == 1.0
    assert window.required_window_seconds == 1.8
    assert window.refresh_due_before_completion is False


def test_wider_gap_exposes_full_safe_channel_window() -> None:
    window = derive_heavy_attack_decision_window(
        context=_context(next_decision=5.0),
        required_window_seconds=1.8,
    )

    assert window.available_window_seconds == 3.0
    assert window.refresh_due_before_completion is False


def test_same_bar_refresh_shortens_window_and_marks_collision() -> None:
    window = derive_heavy_attack_decision_window(
        context=_context(
            next_decision=5.0,
            next_due=(("combat prayer", "front", 3.2),),
        ),
        required_window_seconds=1.8,
    )

    assert window.available_window_seconds == 1.2
    assert window.refresh_due_before_completion is True


def test_opposite_bar_refresh_does_not_shorten_current_bar_window() -> None:
    window = derive_heavy_attack_decision_window(
        context=_context(
            next_decision=5.0,
            next_due=(("winter's revenge", "back", 2.5),),
        ),
        required_window_seconds=1.8,
    )

    assert window.available_window_seconds == 3.0
    assert window.refresh_due_before_completion is False
