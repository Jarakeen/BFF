from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_meteor_esologs_raw_identity_service import (
    RotationMeteorEsoLogsRawIdentityService,
)


def _db(path: Path) -> Path:
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
    return path


def _event(
    db_path: Path,
    *,
    index: int,
    event_type: str,
    name: str,
    ability_id: int,
    source_id: int = 7,
    cast_track_id: int | None = None,
) -> None:
    payload = json.dumps({"ability": {"name": name}})
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                float(index * 1000),
                event_type,
                source_id,
                ability_id,
                cast_track_id,
                payload,
            ),
        )


def test_missing_database_is_unresolved(tmp_path: Path) -> None:
    report = RotationMeteorEsoLogsRawIdentityService(tmp_path / "missing.db").inspect()
    assert report.rows == ()
    assert report.matching_event_count == 0
    assert report.unresolved


def test_inventories_meteor_family_names_without_crosswalk(tmp_path: Path) -> None:
    db = _db(tmp_path / "logs.db")
    _event(db, index=1, event_type="cast", name="Shooting Star", ability_id=100, cast_track_id=10)
    _event(db, index=2, event_type="damage", name="Shooting Star", ability_id=101, cast_track_id=10)
    _event(db, index=3, event_type="damage", name="Ice Comet", ability_id=201, cast_track_id=11)
    _event(db, index=4, event_type="damage", name="Stampede", ability_id=999)

    report = RotationMeteorEsoLogsRawIdentityService(db).inspect()

    assert report.matching_event_count == 3
    assert report.matching_cast_event_count == 1
    assert {(row.ability_name, row.ability_game_id, row.event_type) for row in report.rows} == {
        ("Shooting Star", 100, "cast"),
        ("Shooting Star", 101, "damage"),
        ("Ice Comet", 201, "damage"),
    }
    assert report.unresolved == ()


def test_reports_family_events_without_cast_anchor(tmp_path: Path) -> None:
    db = _db(tmp_path / "logs.db")
    _event(db, index=1, event_type="damage", name="Meteor", ability_id=300, cast_track_id=12)

    report = RotationMeteorEsoLogsRawIdentityService(db).inspect()

    assert report.matching_event_count == 1
    assert report.matching_cast_event_count == 0
    assert report.unresolved == (
        "Meteor-family raw events were found, but none were cast-like events",
    )


def test_name_match_is_case_insensitive_but_exact_family_only(tmp_path: Path) -> None:
    db = _db(tmp_path / "logs.db")
    _event(db, index=1, event_type="cast", name="meteor", ability_id=400)
    _event(db, index=2, event_type="cast", name="Meteoric Strike", ability_id=401)

    report = RotationMeteorEsoLogsRawIdentityService(db).inspect()

    assert report.matching_event_count == 1
    assert report.rows[0].ability_game_id == 400
