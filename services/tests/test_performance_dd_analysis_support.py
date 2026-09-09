from __future__ import annotations

from services.performance_dd_analysis_support import (
    _critical_rate_percent,
    _decode_event_data,
)


def test_critical_rate_percent_uses_damage_event_counts() -> None:
    assert _critical_rate_percent(100, 37) == 37.0
    assert _critical_rate_percent(3, 2) == 66.7


def test_critical_rate_percent_handles_no_damage_events() -> None:
    assert _critical_rate_percent(0, 0) is None
    assert _critical_rate_percent(-1, 0) is None


def test_critical_rate_clamps_impossible_critical_count() -> None:
    assert _critical_rate_percent(10, 20) == 100.0
    assert _critical_rate_percent(10, -5) == 0.0


def test_decode_event_data_accepts_json_scalar_shape() -> None:
    assert _decode_event_data('[{"type":"damage"},{"type":"damage"}]') == [
        {"type": "damage"},
        {"type": "damage"},
    ]
    assert _decode_event_data("not json") == []
