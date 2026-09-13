from __future__ import annotations

import sqlite3

import pytest

from services.rotation_dd_periodic_esologs_trigger_cooccurrence_service import (
    RotationDDPeriodicEsoLogsTriggerCooccurrenceService,
)


def _logs(path):
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
                hit_type TEXT,
                amount REAL,
                tick INTEGER,
                cast_track_id INTEGER
            )
            """
        )


def _event(
    path,
    index,
    time,
    ability_id,
    *,
    target=7,
    hit_type="normal",
    amount=100.0,
    tick=0,
    track=12,
):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                time,
                "damage",
                42,
                target,
                ability_id,
                hit_type,
                amount,
                tick,
                track,
            ),
        )


def test_reports_trigger_coincident_row_and_next_periodic_occurrence(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000.0, 40469, amount=500.0, tick=0)
    _event(logs, 2, 1001.0, 40468, amount=120.0, tick=1)
    _event(logs, 3, 3040.0, 40468, amount=121.0, tick=1)

    report = RotationDDPeriodicEsoLogsTriggerCooccurrenceService(logs).inspect(
        trigger_ability_id=40469,
        periodic_ability_id=40468,
        tolerance_ms=50.0,
    )

    assert report.unresolved == ()
    assert report.trigger_count == 1
    assert report.coincident_trigger_count == 1
    assert len(report.observations) == 1
    observation = report.observations[0]
    assert observation.offset_seconds == pytest.approx(0.001)
    assert observation.periodic_tick is True
    assert observation.same_target is True
    assert observation.same_cast_track is True
    assert observation.next_offset_seconds == pytest.approx(2.04)
    assert observation.next_periodic_tick is True


def test_ignores_periodic_rows_outside_coincident_tolerance(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000.0, 40469)
    _event(logs, 2, 3040.0, 40468, tick=1)

    report = RotationDDPeriodicEsoLogsTriggerCooccurrenceService(logs).inspect(
        trigger_ability_id=40469,
        periodic_ability_id=40468,
        tolerance_ms=50.0,
    )

    assert report.trigger_count == 1
    assert report.coincident_trigger_count == 0
    assert report.observations == ()
    assert any("no periodic ability 40468 rows occurred" in item for item in report.unresolved)


def test_database_is_opened_read_only(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    service = RotationDDPeriodicEsoLogsTriggerCooccurrenceService(logs)

    with service._open_logs() as db:
        with pytest.raises(sqlite3.OperationalError):
            db.execute("CREATE TABLE forbidden_write (id INTEGER)")
