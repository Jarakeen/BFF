import json
import sqlite3

from services.rotation_dd_periodic_esologs_raw_spatial_metadata_service import (
    RotationDDPeriodicEsoLogsRawSpatialMetadataService,
)


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                target_id INTEGER,
                ability_game_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _event(path, *, target_id, ability_id, payload):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            INSERT INTO log_event(report_code, fight_id, target_id, ability_game_id, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("REPORT", 1, target_id, ability_id, json.dumps(payload)),
        )


def test_missing_logs_database_is_unresolved(tmp_path) -> None:
    report = RotationDDPeriodicEsoLogsRawSpatialMetadataService(
        tmp_path / "missing.db"
    ).inspect(118766)

    assert report.event_count == 0
    assert report.fields == ()
    assert "database not found" in report.unresolved[0]


def test_spatial_like_raw_keys_are_inventoried_without_interpretation(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(
        logs,
        target_id=99,
        ability_id=118766,
        payload={
            "type": "damage",
            "x": 12.5,
            "y": 8.25,
            "sourcePosition": {"x": 1.0, "y": 2.0},
            "target": {"distance": 4.5, "name": "Dummy"},
        },
    )
    _event(
        logs,
        target_id=100,
        ability_id=118766,
        payload={
            "type": "damage",
            "x": 13.5,
            "y": 9.25,
            "sourcePosition": {"x": 1.5, "y": 2.5},
            "target": {"distance": 6.0, "name": "Other Dummy"},
        },
    )

    report = RotationDDPeriodicEsoLogsRawSpatialMetadataService(logs).inspect(118766)

    assert report.event_count == 2
    assert report.target_actor_count == 2
    by_path = {field.path: field for field in report.fields}
    assert "x" in by_path
    assert "y" in by_path
    assert "sourcePosition" in by_path
    assert "sourcePosition.x" in by_path
    assert "sourcePosition.y" in by_path
    assert "target.distance" in by_path
    assert by_path["target.distance"].occurrence_count == 2
    assert set(by_path["target.distance"].rendered_values) == {"4.5", "6.0"}
    assert report.unresolved == ()


def test_non_spatial_raw_keys_do_not_get_promoted(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(
        logs,
        target_id=99,
        ability_id=118766,
        payload={
            "type": "damage",
            "timestamp": 12345,
            "amount": 900,
            "sourceID": 42,
            "targetID": 99,
        },
    )

    report = RotationDDPeriodicEsoLogsRawSpatialMetadataService(logs).inspect(118766)

    assert report.event_count == 1
    assert report.fields == ()
    assert "no position/coordinate/location/distance/range" in report.unresolved[0]


def test_only_requested_ability_is_inspected(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, target_id=99, ability_id=118766, payload={"distance": 5})
    _event(logs, target_id=100, ability_id=999999, payload={"distance": 99})

    report = RotationDDPeriodicEsoLogsRawSpatialMetadataService(logs).inspect(118766)

    assert report.event_count == 1
    assert report.fields[0].rendered_values == ("5",)


def test_invalid_ability_id_is_rejected(tmp_path) -> None:
    service = RotationDDPeriodicEsoLogsRawSpatialMetadataService(tmp_path / "logs.db")

    try:
        service.inspect(0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
