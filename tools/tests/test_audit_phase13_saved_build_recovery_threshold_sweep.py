from types import SimpleNamespace

import pytest

from tools.audit_phase13_saved_build_recovery_threshold_sweep import (
    _parse_thresholds,
    minimum_timeline_point,
)


def test_minimum_timeline_point_returns_first_true_minimum() -> None:
    timeline = SimpleNamespace(
        starting_amount=10000,
        events=(
            SimpleNamespace(time_seconds=2.0, after=8000),
            SimpleNamespace(time_seconds=4.0, after=5000),
            SimpleNamespace(time_seconds=6.0, after=7000),
            SimpleNamespace(time_seconds=8.0, after=5000),
        ),
    )

    assert minimum_timeline_point(timeline) == (4.0, 5000)


def test_minimum_timeline_point_handles_no_events() -> None:
    timeline = SimpleNamespace(starting_amount=31109, events=())

    assert minimum_timeline_point(timeline) == (0.0, 31109)


def test_parse_thresholds_preserves_explicit_order() -> None:
    assert _parse_thresholds("0.35, 0.5,0.75") == (0.35, 0.5, 0.75)


def test_parse_thresholds_rejects_empty_or_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _parse_thresholds("")

    with pytest.raises(ValueError, match="between 0 and 1"):
        _parse_thresholds("0.35,1.4")
