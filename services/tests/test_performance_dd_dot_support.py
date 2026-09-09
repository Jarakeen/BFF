from __future__ import annotations

from services.performance_dd_dot_support import (
    _coverage_seconds_from_ticks,
    _entry_log_ability_id,
    _event_log_ability_id,
    _observed_dot_uptimes,
)


def test_report_local_ability_ids_are_transient_correlation_only() -> None:
    assert _entry_log_ability_id({"guid": "1234"}) == 1234
    assert _event_log_ability_id({"abilityGameID": 1234}) == 1234
    assert _entry_log_ability_id({"name": "No Id"}) is None


def test_tick_coverage_splits_long_gaps() -> None:
    # 2s cadence: first three ticks cover 0-6s, then a long gap, then 20-24s.
    coverage = _coverage_seconds_from_ticks(
        [0, 2000, 4000, 20000, 22000],
        fight_start_ms=0,
        fight_end_ms=30000,
    )
    assert coverage == 10.0


def test_single_tick_is_not_enough_to_claim_uptime() -> None:
    assert _coverage_seconds_from_ticks([5000], 0, 30000) == 0.0


def test_observed_dot_uptimes_use_readable_names_and_percent() -> None:
    events = [
        {"timestamp": 0, "abilityGameID": 11},
        {"timestamp": 2000, "abilityGameID": 11},
        {"timestamp": 4000, "abilityGameID": 11},
        {"timestamp": 0, "abilityGameID": 22},
        {"timestamp": 1000, "abilityGameID": 22},
    ]
    rows = _observed_dot_uptimes(
        events,
        {11: "Burning Embers", 22: "Poison Injection"},
        fight_start_ms=0,
        fight_end_ms=10000,
        denominator_seconds=10.0,
    )

    assert [row.Name for row in rows] == ["Burning Embers", "Poison Injection"]
    assert rows[0].UptimeSeconds == 6.0
    assert rows[0].UptimePercent == 60.0
    assert rows[1].UptimePercent == 20.0


def test_unmapped_numeric_ids_do_not_become_display_identity() -> None:
    rows = _observed_dot_uptimes(
        [{"timestamp": 0, "abilityGameID": 999}, {"timestamp": 1000, "abilityGameID": 999}],
        {},
        fight_start_ms=0,
        fight_end_ms=10000,
        denominator_seconds=10.0,
    )
    assert rows == []
