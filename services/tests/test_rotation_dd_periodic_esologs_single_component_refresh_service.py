from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_single_component_refresh_service import (
    RotationDDPeriodicEsoLogsSingleComponentRefreshService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "unnerving_boneyard"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=1, morph=1, base_ability_id=115252),
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
                ability_game_id INTEGER,
                cast_track_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _event(path, index, timestamp, event_type, ability_id, track, *, name=None) -> None:
    raw = {} if name is None else {"ability": {"name": name}}
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                42,
                ability_id,
                track,
                json.dumps(raw),
            ),
        )


def _service(tmp_path):
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    canonical.touch()
    _logs(logs)
    service = RotationDDPeriodicEsoLogsSingleComponentRefreshService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    service._numeric_aliases = lambda skill_id, morph, base_ability_id: (115252,)
    return service, logs


def test_reports_old_stream_relative_to_first_new_periodic_event(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 115252, 10, name="Unnerving Boneyard")
    _event(logs, 2, 1350, "damage", 117809, 10)
    _event(logs, 3, 2350, "damage", 117809, 10)
    _event(logs, 4, 3000, "cast", 115252, 20, name="Unnerving Boneyard")
    _event(logs, 5, 3350, "damage", 117809, 20)
    _event(logs, 6, 4350, "damage", 117809, 20)

    report = service.inspect(
        "unnerving_boneyard",
        periodic_ability_id=117809,
        active_window_seconds=10.0,
    )

    assert report.unresolved == ()
    assert len(report.observations) == 1
    observation = report.observations[0]
    assert observation.old_periodic_before_boundary == 2
    assert observation.old_periodic_at_boundary == 0
    assert observation.old_periodic_after_boundary == 0
    assert observation.last_old_periodic_offset_seconds == -1.0
    assert report.old_tick_at_boundary_count == 0
    assert report.old_tick_after_boundary_count == 0


def test_reports_old_stream_at_and_after_new_stream_boundary(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 115252, 10, name="Unnerving Boneyard")
    _event(logs, 2, 1350, "damage", 117809, 10)
    _event(logs, 3, 3000, "cast", 115252, 20, name="Unnerving Boneyard")
    _event(logs, 4, 3350, "damage", 117809, 20)
    _event(logs, 5, 3370, "damage", 117809, 10)
    _event(logs, 6, 3500, "damage", 117809, 10)

    report = service.inspect(
        "unnerving_boneyard",
        periodic_ability_id=117809,
        active_window_seconds=10.0,
        boundary_tolerance_ms=50.0,
    )

    observation = report.observations[0]
    assert observation.old_periodic_at_boundary == 1
    assert observation.old_periodic_after_boundary == 1
    assert report.old_tick_at_boundary_count == 1
    assert report.old_tick_after_boundary_count == 1


def test_exact_boundary_old_ticks_use_event_order(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 115252, 10, name="Unnerving Boneyard")
    _event(logs, 2, 1350, "damage", 117809, 10)
    _event(logs, 3, 3000, "cast", 115252, 20, name="Unnerving Boneyard")
    _event(logs, 4, 3350, "damage", 117809, 10)
    _event(logs, 5, 3350, "damage", 117809, 20)
    _event(logs, 6, 3350, "damage", 117809, 10)

    report = service.inspect(
        "unnerving_boneyard",
        periodic_ability_id=117809,
        active_window_seconds=10.0,
        boundary_tolerance_ms=0.0,
    )

    observation = report.observations[0]
    assert observation.new_boundary_event_index == 5
    assert observation.exact_boundary_old_tick_event_indices == (4, 6)
    assert observation.exact_boundary_old_tick_before_new == 1
    assert observation.exact_boundary_old_tick_after_new == 1
    assert report.exact_boundary_old_tick_before_new_count == 1
    assert report.exact_boundary_old_tick_after_new_count == 1


def test_missing_linked_periodic_streams_fails_closed(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 115252, 10, name="Unnerving Boneyard")
    _event(logs, 2, 1350, "damage", 117809, 10)

    report = service.inspect(
        "unnerving_boneyard",
        periodic_ability_id=117809,
        active_window_seconds=10.0,
    )

    assert report.observations == ()
    assert any("no consecutive cast pairs" in item for item in report.unresolved)


def test_logs_database_is_not_mutated(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 115252, 10, name="Unnerving Boneyard")
    _event(logs, 2, 1350, "damage", 117809, 10)
    before = logs.read_bytes()

    service.inspect(
        "unnerving_boneyard",
        periodic_ability_id=117809,
        active_window_seconds=10.0,
    )

    assert logs.read_bytes() == before
