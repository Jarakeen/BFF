from __future__ import annotations

import pytest

from services.performance_healer_analysis_support import (
    _analyze_healer_response,
    _critical_rate_percent,
    _observed_hot_uptimes,
    _select_high_damage_events,
    _support_cast_timestamps,
)


def test_healer_critical_rate_is_bounded_and_optional() -> None:
    assert _critical_rate_percent(100, 37) == 37.0
    assert _critical_rate_percent(5, 99) == 100.0
    assert _critical_rate_percent(0, 0) is None


def test_observed_hot_uptime_uses_readable_report_local_names() -> None:
    events = [
        {"timestamp": 0, "abilityGameID": 11},
        {"timestamp": 2000, "abilityGameID": 11},
        {"timestamp": 4000, "abilityGameID": 11},
        {"timestamp": 6000, "abilityGameID": 11},
    ]
    rows = _observed_hot_uptimes(
        events,
        {11: "Radiating Regeneration"},
        fight_start_ms=0,
        fight_end_ms=10_000,
        denominator_seconds=10.0,
    )

    assert len(rows) == 1
    assert rows[0].Name == "Radiating Regeneration"
    assert rows[0].UptimeSeconds == 8.0
    assert rows[0].UptimePercent == 80.0


def test_observed_hot_uptime_needs_more_than_one_tick() -> None:
    rows = _observed_hot_uptimes(
        [{"timestamp": 1000, "abilityGameID": 11}],
        {11: "Echoing Vigor"},
        fight_start_ms=0,
        fight_end_ms=10_000,
        denominator_seconds=10.0,
    )
    assert rows == []


def test_high_damage_sample_selects_upper_quartile_without_universal_threshold() -> None:
    events = [
        {"timestamp": index * 1000, "amount": amount, "targetID": 1}
        for index, amount in enumerate([10, 20, 30, 40, 50, 60, 70, 80])
    ]
    selected = _select_high_damage_events(events)

    assert [event["amount"] for event in selected] == [70, 80]


def test_healer_response_separates_precoverage_and_reactive_healing() -> None:
    damage = [
        {"timestamp": 5000, "amount": 1000, "targetID": 1},
        {"timestamp": 8000, "amount": 1100, "targetID": 2},
        {"timestamp": 12_000, "amount": 1200, "targetID": 3},
        {"timestamp": 16_000, "amount": 1300, "targetID": 4},
    ]
    healing = [
        {"timestamp": 5500, "targetID": 1},
        {"timestamp": 16_700, "targetID": 4},
    ]
    periodic = [
        {"timestamp": 11_500, "targetID": 3},
    ]

    result = _analyze_healer_response(damage, healing, periodic)

    # Upper-quartile sample from four events selects only the largest event.
    assert result.SelectedDamageEvents == 1
    assert result.PrecoveredEvents == 0
    assert result.RespondedEvents == 1
    assert result.UnansweredEvents == 0
    assert result.MedianResponseMs == 700.0


def test_healer_response_marks_precovered_without_calling_it_reactive() -> None:
    damage = [{"timestamp": 10_000, "amount": 5000, "targetID": 7}]
    periodic = [{"timestamp": 9500, "targetID": 7}]

    result = _analyze_healer_response(damage, [], periodic)

    assert result.SelectedDamageEvents == 1
    assert result.PrecoveredEvents == 1
    assert result.RespondedEvents == 0
    assert result.UnansweredEvents == 0
    assert result.MedianResponseMs is None


def test_support_cast_timestamps_count_heavy_attacks_and_synergies_but_not_light_attacks() -> None:
    names = {
        1: "Light Attack",
        2: "Energy Orb",
        3: "Heavy Attack",
        4: "Purify Synergy",
        5: "Weapon Swap",
    }
    events = [
        {"timestamp": 1000, "abilityGameID": 1, "castTrackID": 1},
        {"timestamp": 2000, "abilityGameID": 2, "castTrackID": 2},
        {"timestamp": 3000, "abilityGameID": 3, "castTrackID": 3},
        {"timestamp": 4000, "abilityGameID": 4, "castTrackID": 4},
        {"timestamp": 5000, "abilityGameID": 5, "castTrackID": 5},
    ]

    assert _support_cast_timestamps(events, names) == (2000.0, 3000.0, 4000.0)


def test_healer_response_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="windows"):
        _analyze_healer_response([], [], [], response_window_ms=0)
