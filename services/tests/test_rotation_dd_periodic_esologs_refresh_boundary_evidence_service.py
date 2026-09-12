from __future__ import annotations

import json
import sqlite3

from services.rotation_dd_periodic_esologs_refresh_boundary_evidence_service import (
    RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService,
)


def _canonical(path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute(
            "INSERT INTO skill_rank (id, skill_id, ability_id, morph) VALUES (1, 7, 39807, 1)"
        )
        db.execute(
            "CREATE TABLE skill_entity (entity_id TEXT, skill_rank_id INTEGER)"
        )
        db.execute(
            "INSERT INTO skill_entity (entity_id, skill_rank_id) VALUES ('stampede', 1)"
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
    _canonical(canonical)
    _logs(logs)
    return (
        RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService(
            canonical_database_path=canonical,
            logs_database_path=logs,
        ),
        logs,
    )


def test_reports_old_periodic_events_relative_to_next_impact(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 39807, 10, name="Stampede")
    _event(logs, 2, 1150, "damage", 38792, 10)
    _event(logs, 3, 2150, "damage", 126474, 10)
    _event(logs, 4, 3150, "damage", 126474, 10)
    _event(logs, 5, 4000, "cast", 39807, 20, name="Stampede")
    _event(logs, 6, 4200, "damage", 38792, 20)
    _event(logs, 7, 5200, "damage", 126474, 20)

    report = service.inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
    )

    assert report.unresolved == ()
    assert len(report.observations) == 1
    observation = report.observations[0]
    assert observation.old_periodic_before_boundary == 2
    assert observation.old_periodic_at_boundary == 0
    assert observation.old_periodic_after_boundary == 0
    assert observation.last_old_periodic_offset_seconds == -1.05
    assert observation.first_new_periodic_offset_seconds == 1.0
    assert report.old_tick_at_boundary_count == 0
    assert report.old_tick_after_boundary_count == 0


def test_reports_old_tick_at_and_after_new_impact_without_promoting_policy(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 39807, 10, name="Stampede")
    _event(logs, 2, 1150, "damage", 38792, 10)
    _event(logs, 3, 2150, "damage", 126474, 10)
    _event(logs, 4, 4000, "cast", 39807, 20, name="Stampede")
    _event(logs, 5, 4200, "damage", 38792, 20)
    _event(logs, 6, 4220, "damage", 126474, 10)
    _event(logs, 7, 4400, "damage", 126474, 10)
    _event(logs, 8, 5200, "damage", 126474, 20)

    report = service.inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
        boundary_tolerance_ms=50.0,
    )

    observation = report.observations[0]
    assert observation.old_periodic_at_boundary == 1
    assert observation.old_periodic_after_boundary == 1
    assert report.old_tick_at_boundary_count == 1
    assert report.old_tick_after_boundary_count == 1


def test_missing_consecutive_linked_impacts_fails_closed(tmp_path) -> None:
    service, logs = _service(tmp_path)
    _event(logs, 1, 1000, "cast", 39807, 10, name="Stampede")
    _event(logs, 2, 1150, "damage", 38792, 10)

    report = service.inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
    )

    assert report.observations == ()
    assert any("no consecutive cast pairs" in item for item in report.unresolved)
