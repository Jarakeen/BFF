from types import SimpleNamespace

from services.esologs_event_interpreter import SemanticEventKind
from tools.audit_phase13_healer_effect_alias_candidates import _candidate_rows


def _event(timestamp, *, ability_id, kind=SemanticEventKind.HEAL, source_id=7, tick=True, raw_type="hot"):
    return SimpleNamespace(
        timestamp=timestamp,
        ability_game_id=ability_id,
        event_kind=kind,
        source_id=source_id,
        tick=tick,
        raw_event_type=raw_type,
    )


def _activation(index, timestamp, ability_id=40058):
    return (
        index,
        SimpleNamespace(
            timestamp=timestamp,
            ability_game_id=ability_id,
        ),
    )


def test_candidate_rows_rank_repeated_tick_id_across_windows_first():
    activations = (
        _activation(1, 10000),
        _activation(20, 30000),
    )
    events = (
        _event(11000, ability_id=40059),
        _event(12000, ability_id=40059),
        _event(31000, ability_id=40059),
        _event(32000, ability_id=40059),
        _event(11500, ability_id=99999),
        _event(50000, ability_id=77777),
    )

    rows = _candidate_rows(
        events,
        activations=activations,
        duration_seconds=12.0,
        caster_id=7,
        scale=0.001,
    )

    assert rows[0].ability_game_id == 40059
    assert rows[0].windows_seen == 2
    assert rows[0].total_events == 4
    assert rows[0].tick_events == 4
    assert rows[0].first_offset_seconds == 1.0
    assert rows[0].last_offset_seconds == 2.0


def test_candidate_rows_ignore_other_casters_and_events_outside_window():
    activations = (_activation(1, 10000),)
    events = (
        _event(11000, ability_id=40059, source_id=8),
        _event(23000, ability_id=40059),
        _event(11500, ability_id=40059),
    )

    rows = _candidate_rows(
        events,
        activations=activations,
        duration_seconds=12.0,
        caster_id=7,
        scale=0.001,
    )

    assert len(rows) == 1
    assert rows[0].ability_game_id == 40059
    assert rows[0].total_events == 1


def test_candidate_rows_truncate_window_at_next_recast():
    activations = (
        _activation(1, 10000),
        _activation(10, 15000),
    )
    events = (
        _event(12000, ability_id=40059),
        _event(16000, ability_id=40059),
    )

    rows = _candidate_rows(
        events,
        activations=activations,
        duration_seconds=12.0,
        caster_id=7,
        scale=0.001,
    )

    row = rows[0]
    assert row.windows_seen == 2
    assert row.total_events == 2
    assert row.first_offset_seconds == 1.0
    assert row.last_offset_seconds == 2.0
