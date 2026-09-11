from types import SimpleNamespace

from tools.audit_phase13_staff_heavy_attack_restore_corpus import (
    _completed_staff_heavies,
    _following_restores,
    _heavy_event_shape_key,
    _normalize_player_details,
)
from services.esologs_event_interpreter import SemanticEventKind


def _heavy_event(
    *,
    ability_game_id,
    source_id=7,
    timestamp,
    event_index,
    raw_event_type,
    cast_track_id=None,
    tick=None,
):
    return SimpleNamespace(
        ability_game_id=ability_game_id,
        source_id=source_id,
        timestamp=timestamp,
        event_index=event_index,
        raw_event_type=raw_event_type,
        cast_track_id=cast_track_id,
        tick=tick,
    )


def test_normalize_player_details_keeps_role_name_and_actor_id():
    rows = _normalize_player_details(
        {
            "healers": [{"id": 7, "name": "Anonymous 7"}],
            "tanks": [{"id": 4, "name": "Anonymous 4"}],
            "dps": [{"id": 10, "name": "Anonymous 10"}],
        }
    )

    assert rows == (
        (7, "Anonymous 7", "healer"),
        (4, "Anonymous 4", "tank"),
        (10, "Anonymous 10", "dps"),
    )


def test_following_restores_filters_self_target_source_positive_amount_and_window():
    events = (
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            target_id=7,
            timestamp=1100.0,
            resource_change=2400.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            target_id=8,
            timestamp=1100.0,
            resource_change=125.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=8,
            target_id=8,
            timestamp=1100.0,
            resource_change=9999.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            target_id=7,
            timestamp=1700.0,
            resource_change=3000.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            target_id=7,
            timestamp=1200.0,
            resource_change=-20.0,
        ),
    )

    rows = _following_restores(events, source_id=7, timestamp=1000.0, forward_ms=500.0)

    assert len(rows) == 1
    assert rows[0][0].resource_change == 2400.0
    assert rows[0][0].target_id == 7
    assert rows[0][1] == 100.0


def test_heavy_event_shape_key_preserves_raw_type_tick_and_cast_tracking():
    event = SimpleNamespace(
        raw_event_type="damage",
        tick=False,
        cast_track_id=91234,
    )

    assert _heavy_event_shape_key("frost_staff_heavy", event) == (
        "frost_staff_heavy",
        "damage",
        False,
        True,
    )


def test_completed_staff_heavies_pairs_channel_cast_to_removedebuff_and_fails_closed_unpaired():
    events = (
        _heavy_event(
            ability_game_id=16212,
            timestamp=1000.0,
            event_index=1,
            raw_event_type="cast",
            cast_track_id=42,
        ),
        _heavy_event(
            ability_game_id=16212,
            timestamp=1500.0,
            event_index=2,
            raw_event_type="damage",
            cast_track_id=42,
            tick=True,
        ),
        _heavy_event(
            ability_game_id=16212,
            timestamp=2500.0,
            event_index=3,
            raw_event_type="removedebuff",
        ),
        _heavy_event(
            ability_game_id=16212,
            timestamp=9000.0,
            event_index=4,
            raw_event_type="removedebuff",
        ),
    )

    rows = _completed_staff_heavies(events)

    assert len(rows) == 1
    label, completion, start, effective_track = rows[0]
    assert label == "restoration_staff_heavy"
    assert completion.event_index == 3
    assert completion.raw_event_type == "removedebuff"
    assert start.event_index == 1
    assert effective_track == 42


def test_completed_staff_heavies_uses_charge_release_cast_and_preserves_begin_track_when_available():
    events = (
        _heavy_event(
            ability_game_id=16261,
            timestamp=1000.0,
            event_index=1,
            raw_event_type="begincast",
            cast_track_id=99,
        ),
        _heavy_event(
            ability_game_id=16261,
            timestamp=2200.0,
            event_index=2,
            raw_event_type="cast",
        ),
        _heavy_event(
            ability_game_id=16261,
            timestamp=5000.0,
            event_index=3,
            raw_event_type="cast",
        ),
    )

    rows = _completed_staff_heavies(events)

    assert len(rows) == 2
    assert rows[0][0] == "frost_staff_heavy"
    assert rows[0][1].event_index == 2
    assert rows[0][2].event_index == 1
    assert rows[0][3] == 99
    assert rows[1][1].event_index == 3
    assert rows[1][2] is None
    assert rows[1][3] is None
