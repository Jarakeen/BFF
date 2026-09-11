from types import SimpleNamespace

from tools.audit_phase13_staff_heavy_attack_restore_corpus import (
    _following_restores,
    _normalize_player_details,
)
from services.esologs_event_interpreter import SemanticEventKind


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


def test_following_restores_filters_source_positive_amount_and_window():
    events = (
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            timestamp=1100.0,
            resource_change=2400.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=8,
            timestamp=1100.0,
            resource_change=9999.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            timestamp=1700.0,
            resource_change=3000.0,
        ),
        SimpleNamespace(
            event_kind=SemanticEventKind.RESOURCE_CHANGE,
            source_id=7,
            timestamp=1200.0,
            resource_change=-20.0,
        ),
    )

    rows = _following_restores(events, source_id=7, timestamp=1000.0, forward_ms=500.0)

    assert len(rows) == 1
    assert rows[0][0].resource_change == 2400.0
    assert rows[0][1] == 100.0
