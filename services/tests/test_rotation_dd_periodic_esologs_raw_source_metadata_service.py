import json
import sqlite3

from services.rotation_dd_periodic_esologs_raw_source_metadata_service import (
    RotationDDPeriodicEsoLogsRawSourceMetadataService,
)


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                source_id INTEGER,
                ability_game_id INTEGER,
                raw_json TEXT
            )
            """
        )
        db.commit()


def test_inventories_nested_source_and_owner_like_raw_fields(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    payload = {
        "sourceInstance": 3,
        "ability": {"name": "Skeleton Arrow"},
        "extra": {
            "ownerID": 42,
            "petMetadata": {"summonType": "Skeletal Archer"},
        },
    }
    with sqlite3.connect(logs) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?)",
            ("REPORT", 1, 500, 122774, json.dumps(payload)),
        )
        db.commit()

    report = RotationDDPeriodicEsoLogsRawSourceMetadataService(logs).inspect(122774)

    assert report.event_count == 1
    assert report.source_actor_count == 1
    by_path = {field.path: field for field in report.fields}
    assert "sourceInstance" in by_path
    assert "extra.ownerID" in by_path
    assert "extra.petMetadata" in by_path
    assert "extra.petMetadata.summonType" in by_path
    assert report.unresolved == ()


def test_reports_absent_source_like_metadata_without_guessing(tmp_path) -> None:
    logs = tmp_path / "logs.db"
    _logs(logs)
    with sqlite3.connect(logs) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?)",
            (
                "REPORT",
                1,
                500,
                122774,
                json.dumps({"ability": {"name": "Skeleton Arrow"}, "amount": 100}),
            ),
        )
        db.commit()

    report = RotationDDPeriodicEsoLogsRawSourceMetadataService(logs).inspect(122774)

    assert report.fields == ()
    assert any("no source/owner" in item for item in report.unresolved)
