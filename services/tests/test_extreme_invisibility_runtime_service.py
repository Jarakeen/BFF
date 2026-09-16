from __future__ import annotations

import pytest

from services.extreme_invisibility_runtime_service import (
    ExtremeInvisibilityRuntimeService,
)
from services.runtime_interval_coverage_service import RuntimeInterval


def test_overlapping_invisibility_windows_share_one_coverage_truth() -> None:
    result = ExtremeInvisibilityRuntimeService.evaluate(
        (
            RuntimeInterval(0.0, 4.0, "cloak one"),
            RuntimeInterval(3.0, 7.0, "cloak two"),
            RuntimeInterval(10.0, 12.0, "cloak three"),
        ),
        duration_seconds=20.0,
    )

    assert result.longest_contiguous_seconds == pytest.approx(7.0)
    assert result.covered_seconds == pytest.approx(9.0)
    assert result.uptime_ratio == pytest.approx(0.45)
    assert result.window_count == 2
    assert result.mechanic_complete is True


def test_touching_windows_are_contiguous_and_clipped_to_duration() -> None:
    result = ExtremeInvisibilityRuntimeService.evaluate(
        (
            RuntimeInterval(2.0, 5.0, "first"),
            RuntimeInterval(5.0, 9.0, "second"),
            RuntimeInterval(9.0, 15.0, "third"),
        ),
        duration_seconds=12.0,
    )

    assert result.longest_contiguous_seconds == pytest.approx(10.0)
    assert result.covered_seconds == pytest.approx(10.0)
    assert result.uptime_ratio == pytest.approx(10.0 / 12.0)
    assert result.window_count == 1


def test_unresolved_source_discovery_blocks_complete_claim_without_corrupting_timeline() -> None:
    result = ExtremeInvisibilityRuntimeService.evaluate(
        (RuntimeInterval(0.0, 3.0, "reviewed window"),),
        duration_seconds=10.0,
        unresolved=("Shadow Cloak duration source not yet enumerated",),
    )

    assert result.longest_contiguous_seconds == pytest.approx(3.0)
    assert result.uptime_ratio == pytest.approx(0.3)
    assert result.mechanic_complete is False
