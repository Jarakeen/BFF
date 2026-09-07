from __future__ import annotations

import pytest

from tools.audit_phase13_xalvakka_healer_lead_boundary import (
    _lead_from_candidate_id,
    _lead_grid,
)


def test_lead_grid_includes_fractional_stop_without_float_drift() -> None:
    assert _lead_grid(1.0, 3.0, 0.5) == (1.0, 1.5, 2.0, 2.5, 3.0)


def test_lead_grid_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="start-seconds must be positive"):
        _lead_grid(0.0, 3.0, 0.5)
    with pytest.raises(ValueError, match="stop-seconds must be greater"):
        _lead_grid(3.0, 2.0, 0.5)
    with pytest.raises(ValueError, match="step-seconds must be positive"):
        _lead_grid(1.0, 3.0, 0.0)


def test_lead_candidate_id_parser_preserves_baseline_boundary() -> None:
    assert _lead_from_candidate_id("seeds-7.5s-early") == 7.5
    assert _lead_from_candidate_id("baseline") is None
    assert _lead_from_candidate_id("demand-aware-0s") is None
    assert _lead_from_candidate_id("seeds-not-a-number-s-early") is None
