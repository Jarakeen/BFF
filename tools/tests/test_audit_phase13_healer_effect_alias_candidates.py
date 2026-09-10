from types import SimpleNamespace

from services.esologs_event_interpreter import SemanticEventKind
from tools.audit_phase13_healer_effect_alias_candidates import (
    EffectAliasCandidate,
    _aggregate_rows,
    _candidate_rows,
    build_parser,
)


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


def test_aggregate_rows_combines_candidate_evidence_across_fights():
    fight_rows = (
        (
            6,
            (
                EffectAliasCandidate(
                    ability_game_id=40059,
                    windows_seen=3,
                    total_events=12,
                    tick_events=12,
                    first_offset_seconds=0.1,
                    last_offset_seconds=11.9,
                ),
            ),
        ),
        (
            27,
            (
                EffectAliasCandidate(
                    ability_game_id=40059,
                    windows_seen=4,
                    total_events=16,
                    tick_events=16,
                    first_offset_seconds=0.05,
                    last_offset_seconds=11.95,
                ),
                EffectAliasCandidate(
                    ability_game_id=99999,
                    windows_seen=1,
                    total_events=1,
                    tick_events=0,
                    first_offset_seconds=4.0,
                    last_offset_seconds=4.0,
                ),
            ),
        ),
    )

    rows = _aggregate_rows(fight_rows, total_windows=7)

    assert rows[0].ability_game_id == 40059
    assert rows[0].fights_seen == 2
    assert rows[0].windows_seen == 7
    assert rows[0].total_windows == 7
    assert rows[0].total_events == 28
    assert rows[0].tick_events == 28
    assert rows[0].first_offset_seconds == 0.05
    assert rows[0].last_offset_seconds == 11.95
    assert rows[1].ability_game_id == 99999
    assert rows[1].fights_seen == 1


def test_parser_accepts_repeated_fight_ids():
    args = build_parser().parse_args(
        [
            "--raw",
            "corpus.json",
            "--report-code",
            "REPORT",
            "--fight-id",
            "6",
            "--fight-id",
            "27",
            "--fight-id",
            "41",
            "--caster-id",
            "7",
        ]
    )

    assert args.fight_ids == [6, 27, 41]
    assert args.caster_id == 7
