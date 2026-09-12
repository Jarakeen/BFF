from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "stampede"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=7, morph=1, base_ability_id=39807),
            unresolved=(),
        )


def _logs(path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                target_id INTEGER,
                ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                cast_track_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _event(
    path,
    index,
    timestamp,
    event_type,
    *,
    source=42,
    target=None,
    ability=None,
    amount=None,
    hit_type=None,
    track=None,
    name=None,
) -> None:
    raw = {} if name is None else {"ability": {"name": name}}
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                source,
                target,
                ability,
                amount,
                hit_type,
                track,
                json.dumps(raw),
            ),
        )


def _service(tmp_path):
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    canonical.touch()
    _logs(logs)
    service = RotationDDPeriodicEsoLogsMagnitudeStateTransitionService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    service._numeric_aliases = lambda skill_id, morph, base_ability_id: (39807,)
    return service, logs


def test_correlates_amount_change_with_state_event_on_damage_source(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", ability=39807, track=10, name="Stampede")
    _event(logs, 2, 2000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)
    _event(logs, 3, 2500, "applybuff", source=42, target=42, ability=61665, name="Test Buff")
    _event(logs, 4, 3000, "damage", target=99, ability=126474, amount=1200, hit_type=1, track=10)

    report = service.inspect("stampede", periodic_ability_id=126474)

    assert report.unresolved == ()
    assert len(report.transitions) == 1
    transition = report.transitions[0]
    assert transition.from_amount == 1000
    assert transition.to_amount == 1200
    assert transition.has_observed_state_change is True
    assert len(transition.state_events) == 1
    assert transition.state_events[0].ability_game_id == 61665
    assert transition.state_events[0].ability_name == "Test Buff"
    assert report.transitions_with_state_change == 1
    assert report.transitions_without_state_change == 0


def test_correlates_amount_change_with_state_event_on_damage_target(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", ability=39807, track=10, name="Stampede")
    _event(logs, 2, 2000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)
    _event(logs, 3, 2500, "applydebuff", source=77, target=99, ability=61743, name="Test Debuff")
    _event(logs, 4, 3000, "damage", target=99, ability=126474, amount=900, hit_type=1, track=10)

    report = service.inspect("stampede", periodic_ability_id=126474)

    assert report.transitions_with_state_change == 1
    assert report.transitions[0].state_events[0].event_type == "applydebuff"
    assert report.transitions[0].state_events[0].target_id == 99


def test_unrelated_state_event_does_not_count(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", ability=39807, track=10, name="Stampede")
    _event(logs, 2, 2000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)
    _event(logs, 3, 2500, "applybuff", source=77, target=77, ability=61665, name="Other Buff")
    _event(logs, 4, 3000, "damage", target=99, ability=126474, amount=1200, hit_type=1, track=10)

    report = service.inspect("stampede", periodic_ability_id=126474)

    assert len(report.transitions) == 1
    assert report.transitions[0].state_events == ()
    assert report.transitions_without_state_change == 1


def test_same_timestamp_state_event_uses_event_index_order(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", ability=39807, track=10, name="Stampede")
    _event(logs, 2, 2000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)
    _event(logs, 3, 3000, "applybuff", source=42, target=42, ability=61665, name="Before Tick")
    _event(logs, 4, 3000, "damage", target=99, ability=126474, amount=1200, hit_type=1, track=10)
    _event(logs, 5, 3000, "applybuff", source=42, target=42, ability=61666, name="After Tick")

    report = service.inspect("stampede", periodic_ability_id=126474)

    assert len(report.transitions[0].state_events) == 1
    assert report.transitions[0].state_events[0].ability_game_id == 61665


def test_constant_amount_pair_does_not_create_transition(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", ability=39807, track=10, name="Stampede")
    _event(logs, 2, 2000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)
    _event(logs, 3, 3000, "damage", target=99, ability=126474, amount=1000, hit_type=1, track=10)

    report = service.inspect("stampede", periodic_ability_id=126474)

    assert report.transitions == ()
    assert any("no same-cast periodic amount-change transitions" in item for item in report.unresolved)
