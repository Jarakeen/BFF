from __future__ import annotations

import pytest

from services.performance_dd_activity_support import _analyze_action_gaps


def test_action_gap_analysis_flags_only_internal_gaps_over_threshold() -> None:
    result = _analyze_action_gaps([1000, 2000, 5500, 6500])

    assert result.GapCount == 1
    assert result.LargestGapSeconds == 3.5
    assert result.ExcessGapSeconds == 1.0
    assert result.Gaps[0].StartTimestampMs == 2000
    assert result.Gaps[0].EndTimestampMs == 5500


def test_action_gap_analysis_excludes_exact_threshold_and_shorter_intervals() -> None:
    result = _analyze_action_gaps([0, 1000, 3500, 5999])

    assert result.GapCount == 0
    assert result.LargestGapSeconds is None
    assert result.ExcessGapSeconds == 0.0
    assert result.Gaps == ()


def test_action_gap_analysis_collapses_duplicate_skill_timestamps() -> None:
    result = _analyze_action_gaps([1000, 1000, 5000])

    assert result.GapCount == 1
    assert result.LargestGapSeconds == 4.0
    assert result.ExcessGapSeconds == 1.5


def test_action_gap_analysis_ranks_longest_gaps_but_sums_all_excess() -> None:
    result = _analyze_action_gaps(
        [0, 3000, 7000, 10_600, 13_200],
        limit=2,
    )

    # Gaps are 3.0s, 4.0s, 3.6s, and 2.6s. With a 2.5s threshold,
    # excess is 0.5 + 1.5 + 1.1 + 0.1 = 3.2s. The display limit only
    # truncates the ranked detail rows; aggregate excess still includes all gaps.
    assert result.GapCount == 4
    assert result.LargestGapSeconds == 4.0
    assert result.ExcessGapSeconds == pytest.approx(3.2)
    assert [gap.DurationSeconds for gap in result.Gaps] == [4.0, 3.6]


def test_action_gap_analysis_requires_positive_threshold() -> None:
    with pytest.raises(ValueError, match="positive"):
        _analyze_action_gaps([1000, 2000], threshold_ms=0)
