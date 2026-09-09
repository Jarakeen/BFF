from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.audit_phase13_lokkestiiz_runtime_evidence import audit


def _database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE log_fight (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                name TEXT,
                kill INTEGER,
                difficulty INTEGER,
                boss_percentage REAL,
                start_time REAL,
                end_time REAL,
                encounter_id INTEGER
            );
            CREATE TABLE log_actor (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                name TEXT,
                display_name TEXT,
                role TEXT,
                actor_type TEXT
            );
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                ability_game_id INTEGER,
                resource_change REAL,
                resource_change_type INTEGER,
                other_resource_change REAL,
                max_resource_amount REAL,
                raw_json TEXT
            );
            """
        )
        connection.execute(
            """
            INSERT INTO log_fight (
                report_code, fight_id, name, kill, difficulty, boss_percentage,
                start_time, end_time, encounter_id
            ) VALUES ('ABC', 6, 'Lokkestiiz', 1, 2, 0, 100000, 250000, 1234)
            """
        )
        connection.execute(
            """
            INSERT INTO log_actor (
                report_code, fight_id, actor_id, name, display_name, role, actor_type
            ) VALUES ('ABC', 6, 7, 'Magrat', '@Jarakeen', 'healer', 'Player')
            """
        )
        for index, timestamp in enumerate((120000, 170000, 220000)):
            connection.execute(
                """
                INSERT INTO log_event (
                    report_code, fight_id, event_index, timestamp, event_type,
                    source_id, source_is_friendly, target_id, ability_game_id,
                    resource_change, resource_change_type, other_resource_change,
                    max_resource_amount, raw_json
                ) VALUES ('ABC', 6, ?, ?, 'begincast', 99, 0, 7, 555,
                          NULL, NULL, NULL, NULL, '{}')
                """,
                (index, timestamp),
            )
        connection.execute(
            """
            INSERT INTO log_event (
                report_code, fight_id, event_index, timestamp, event_type,
                source_id, source_is_friendly, target_id, ability_game_id,
                resource_change, resource_change_type, other_resource_change,
                max_resource_amount, raw_json
            ) VALUES ('ABC', 6, 10, 100250, 'resourcechange', 7, 1, 7, 777,
                      3, 7, 0, 500, ?)
            """,
            (json.dumps({"resourceChangeType": 7}),),
        )
        connection.commit()
    finally:
        connection.close()


def test_audit_reports_imported_fight_healer_raw_signatures_and_resource_samples(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _database(database)

    lines = audit(database_path=database)
    text = "\n".join(lines)

    assert "LOKKESTIIZ_FIGHTS: 1" in text
    assert "FIGHT: report=ABC fight_id=6 name=Lokkestiiz" in text
    assert "HEALER: actor_id=7 name=Magrat display_name=@Jarakeen role=healer" in text
    assert "HOSTILE_SIGNATURE_X3: ability_id=555 event_type=begincast first=20.000s last=120.000s" in text
    assert "HEALER_RESOURCE_TYPES: actor_id=7 7" in text
    assert "HEALER_RESOURCE_SAMPLE: actor_id=7 t=0.250s" in text
    assert "raw_type=7" in text
    assert "RUNTIME_EVIDENCE_READY: false" in text


def test_audit_reports_no_imported_lokkestiiz_fights_without_guessing(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _database(database)
    connection = sqlite3.connect(database)
    try:
        connection.execute("DELETE FROM log_fight")
        connection.commit()
    finally:
        connection.close()

    lines = audit(database_path=database)

    assert "LOKKESTIIZ_FIGHTS: 0" in lines
    assert "RUNTIME_EVIDENCE_READY: false" in lines
    assert "UNRESOLVED: no imported Lokkestiiz fights exist in log_fight" in lines
