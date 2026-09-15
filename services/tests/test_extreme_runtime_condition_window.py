import pytest

from services.extreme_runtime_condition_window import ExtremeRuntimeConditionWindow
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot


def _window(
    condition_id: str = "sacred_ground_window",
    *,
    start: float = 10.0,
    end: float = 14.0,
    sequence: int = 0,
) -> ExtremeRuntimeConditionWindow:
    return ExtremeRuntimeConditionWindow(
        condition_id=condition_id,
        active_from_seconds=start,
        active_until_seconds=end,
        source_evidence="explicit reviewed runtime condition evidence",
        sequence=sequence,
    )


def test_condition_window_is_active_on_inclusive_boundaries_and_expires_after_end() -> None:
    window = _window()
    assert window.active_at(10.0) is True
    assert window.active_at(12.0) is True
    assert window.active_at(14.0) is True
    assert window.active_at(14.001) is False


def test_snapshot_exposes_only_conditions_active_at_exact_snapshot_time() -> None:
    sacred = _window("sacred_ground_window", start=10.0, end=14.0)
    heavy = _window(
        "restoration_staff_heavy_post_completion_window",
        start=8.0,
        end=12.0,
    )
    expired = _window("expired_condition", start=1.0, end=2.0)
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(expired, sacred, heavy),
        snapshot_time_seconds=11.0,
    )

    assert snapshot.condition_windows == (expired, heavy, sacred)
    assert snapshot.active_condition_ids == (
        "restoration_staff_heavy_post_completion_window",
        "sacred_ground_window",
    )


def test_condition_window_orders_with_other_runtime_history_and_survives_snapshot_slice() -> None:
    condition = _window(start=5.0, end=9.0, sequence=1)
    potion = ExtremeRuntimePotionUse(time_seconds=5.0, sequence=0)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(condition, potion),
        snapshot_time_seconds=12.0,
    )

    assert source.ordered_runtime_history == (potion, condition)
    assert source.active_condition_ids == ()

    sliced = source.snapshot_at(7.0)
    assert sliced.condition_windows == (condition,)
    assert sliced.active_condition_ids == ("sacred_ground_window",)


def test_condition_window_validation_fails_closed() -> None:
    with pytest.raises(ValueError, match="runtime condition id"):
        ExtremeRuntimeConditionWindow("", 1.0, 2.0, "evidence")
    with pytest.raises(ValueError, match="requires source evidence"):
        ExtremeRuntimeConditionWindow("condition", 1.0, 2.0, "")
    with pytest.raises(ValueError, match="not precede"):
        ExtremeRuntimeConditionWindow("condition", 3.0, 2.0, "evidence")
    with pytest.raises(ValueError, match="sequence"):
        ExtremeRuntimeConditionWindow("condition", 1.0, 2.0, "evidence", -1)
