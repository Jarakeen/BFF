from __future__ import annotations

import pytest

from services.performance_dd_activity_support import ObservedActionGap
from services.performance_dd_gap_context_support import _classify_action_gap_context


def _gap(start: float, end: float) -> ObservedActionGap:
    return ObservedActionGap(
        StartTimestampMs=start,
        EndTimestampMs=end,
        DurationSeconds=(end - start) / 1000.0,
        ExcessSeconds=max(0.0, (end - start - 2500.0) / 1000.0),
    )


def test_gap_context_marks_raid_quiet_when_group_damage_collapses() -> None:
    result = _classify_action_gap_context(
        [_gap(2000, 5000)],
        [(0, 100), (1, 100), (2, 0), (3, 5), (4, 0), (5, 0), (6, 100)],
        fight_start_ms=0,
    )

    assert result.RaidQuietCount == 1
    assert result.RaidActiveCount == 0
    assert result.UnknownCount == 0
    assert result.Rows[0].Classification == "raid_quiet"


def test_gap_context_marks_raid_active_when_group_keeps_damaging() -> None:
    result = _classify_action_gap_context(
        [_gap(2000, 5000)],
        [(0, 100), (1, 100), (2, 80), (3, 90), (4, 100), (5, 90), (6, 100)],
        fight_start_ms=0,
    )

    assert result.RaidActiveCount == 1
    assert result.Rows[0].Classification == "raid_active"


def test_gap_context_keeps_ambiguous_middle_activity_unknown() -> None:
    result = _classify_action_gap_context(
        [_gap(2000, 5000)],
        [(0, 100), (1, 100), (2, 20), (3, 25), (4, 30), (5, 25), (6, 100)],
        fight_start_ms=0,
    )

    assert result.UnknownCount == 1
    assert result.Rows[0].Classification == "unknown"


def test_gap_context_aligns_report_relative_timestamps_to_graph_seconds() -> None:
    result = _classify_action_gap_context(
        [_gap(102_000, 105_000)],
        [(0, 100), (1, 100), (2, 0), (3, 0), (4, 0), (5, 0), (6, 100)],
        fight_start_ms=100_000,
    )

    assert result.RaidQuietCount == 1


def test_gap_context_is_unknown_without_usable_raid_graph() -> None:
    result = _classify_action_gap_context([_gap(2000, 5000)], [], fight_start_ms=0)

    assert result.UnknownCount == 1
    assert result.Rows[0].RaidActivityRatio is None


def test_gap_context_rejects_overlapping_classification_thresholds() -> None:
    with pytest.raises(ValueError, match="quiet < active"):
        _classify_action_gap_context([], [], 0, quiet_ratio=0.5, active_ratio=0.5)
