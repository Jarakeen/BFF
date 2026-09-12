from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.audit_phase13_xalvakka_manifold_runtime_evidence import audit


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
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
                encounter_id INTEGER,
                raw_json TEXT
            );

            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                target_is_friendly INTEGER,
                ability_game_id INTEGER,
                extra_ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                tick INTEGER,
                cast_track_id INTEGER,
                resource_change REAL,
                resource_change_type INTEGER,
                other_resource_change REAL,
                max_resource_amount REAL,
                waste REAL,
                overheal REAL,
                absorbed REAL,
                stack INTEGER,
                raw_json TEXT
            );
            """
        )
        connection.execute(
            """
            INSERT INTO log_fight (
                report_code, fight_id, name, kill, difficulty, boss_percentage,
                start_time, end_time, encounter_id, raw_json
            ) VALUES ('RGHM', 7, 'Xalvakka', 1, 2, 0, 90000, 150000, 1234, '{}')
            """
        )

        events: list[tuple] = []
        event_index = 1
        cast_payload = json.dumps({"ability": {"name": "Creeping Manifold"}})
        events.append(
            ('RGHM', 7, event_index, 100000, 'cast', 900, 0, None, None, None, 500, None,
             None, None, None, None, None, None, None, None, None, None, None, None, cast_payload)
        )
        event_index += 1
        for timestamp in (100500, 101800, 103100):
            for target_id in (11, 12, 13):
                damage_payload = json.dumps({"ability": {"name": "Creeping Manifold"}})
                events.append(
                    ('RGHM', 7, event_index, timestamp, 'damage', 900, 0, target_id, None, 1,
                     501, None, 15000, None, 1, None, None, None, None, None, None, None, None,
                     None, damage_payload)
                )
                event_index += 1
        connection.executemany(
            """
            INSERT INTO log_event (
                report_code, fight_id, event_index, timestamp, event_type,
                source_id, source_is_friendly, target_id, target_instance,
                target_is_friendly, ability_game_id, extra_ability_game_id,
                amount, hit_type, tick, cast_track_id, resource_change,
                resource_change_type, other_resource_change, max_resource_amount,
                waste, overheal, absorbed, stack, raw_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            events,
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_audit_discovers_xalvakka_and_reports_candidate_runtime_shape(tmp_path: Path) -> None:
    lines = audit(database_path=_database(tmp_path))
    text = "\n".join(lines)

    assert "XALVAKKA_FIGHTS: 1" in text
    assert "report=RGHM fight_id=7" in text
    assert "MANIFOLD_CANDIDATE:" in text
    assert "first_hit_offset=0.500s" in text
    assert "active_width=2.600s" in text
    assert "logical_ticks=0.500,1.800,3.100" in text
    assert "cadence=1.300,1.300" in text
    assert "targets=3" in text
    assert "raw_damage_events=9" in text
    assert "MANIFOLD_CANDIDATES: 1" in text
    assert "MANIFOLD_OBSERVATION_READY: true" in text
    assert "REVIEW_REQUIRED:" in text


def test_audit_fails_closed_when_no_xalvakka_fights_exist(tmp_path: Path) -> None:
    path = _database(tmp_path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DELETE FROM log_fight")
        connection.commit()
    finally:
        connection.close()

    lines = audit(database_path=path)

    assert lines[-2:] == (
        "MANIFOLD_OBSERVATION_READY: false",
        "UNRESOLVED: no imported Xalvakka fights exist in log_fight",
    )
