from types import SimpleNamespace

from tools.audit_phase13_cross_player_heavy_attack_candidates import (
    _follow_resource_events,
    _nearest_preceding_action,
)
from services.esologs_event_interpreter import SemanticEventKind


def _event(**kwargs):
    defaults = dict(
        source_id=7,
        timestamp=1000.0,
        raw_event_type="damage",
        ability_game_id=123,
        ability_name="Heavy Attack Candidate",
        event_kind=SemanticEventKind.DAMAGE,
        resource_change=None,
        resource_change_type=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_nearest_preceding_action_uses_same_source_and_window():
    events = (
        _event(timestamp=600.0, ability_game_id=1),
        _event(timestamp=900.0, ability_game_id=2),
        _event(timestamp=950.0, ability_game_id=3, source_id=99),
        _event(timestamp=990.0, ability_game_id=4, raw_event_type="applybuff"),
    )

    action, delta = _nearest_preceding_action(
        events,
        source_id=7,
        timestamp=1000.0,
        lookback_ms=500.0,
    )

    assert action.ability_game_id == 2
    assert delta == 100.0


def test_follow_resource_events_uses_same_source_forward_window():
    action = _event(timestamp=1000.0, source_id=7)
    events = (
        _event(
            timestamp=1000.0,
            source_id=7,
            raw_event_type="resourcechange",
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            resource_change=3960.0,
            ability_game_id=95042,
        ),
        _event(
            timestamp=1500.0,
            source_id=7,
            raw_event_type="resourcechange",
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            resource_change=1280.0,
            ability_game_id=55678,
        ),
        _event(
            timestamp=1600.0,
            source_id=99,
            raw_event_type="resourcechange",
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            resource_change=9999.0,
        ),
        _event(
            timestamp=2501.0,
            source_id=7,
            raw_event_type="resourcechange",
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            resource_change=7777.0,
        ),
    )

    rows = _follow_resource_events(events, action=action, forward_ms=1000.0)

    assert [(row.resource_change, delta) for row, delta in rows] == [
        (3960.0, 0.0),
        (1280.0, 500.0),
    ]
