from __future__ import annotations

import pytest

from tools.audit_rotation_dd_periodic_esologs_anchor_correlation import (
    _distribution_lines,
    _percentile,
)


def test_percentile_interpolates_ordered_distribution() -> None:
    values = (0.10, 0.20, 0.30, 0.40, 0.50)

    assert _percentile(values, 0.0) == pytest.approx(0.10)
    assert _percentile(values, 0.25) == pytest.approx(0.20)
    assert _percentile(values, 0.50) == pytest.approx(0.30)
    assert _percentile(values, 0.90) == pytest.approx(0.46)
    assert _percentile(values, 1.0) == pytest.approx(0.50)


def test_distribution_lines_report_spread_and_median_bands() -> None:
    lines = _distribution_lines((0.140, 0.144, 0.148, 0.200))
    text = "\n".join(lines)

    assert "count=4" in text
    assert "median=0.146s" in text
    assert "population_stdev=" in text
    assert "within median ±10ms: 3/4 (75.0%)" in text
    assert "within median ±25ms: 3/4 (75.0%)" in text
    assert "within median ±50ms: 4/4 (100.0%)" in text


def test_distribution_lines_handle_empty_evidence() -> None:
    assert _percentile((), 0.50) is None
    assert _distribution_lines(()) == ("  unavailable",)
