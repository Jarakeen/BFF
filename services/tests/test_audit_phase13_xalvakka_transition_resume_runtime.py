import json
import sqlite3
from pathlib import Path

from tools.audit_phase13_xalvakka_transition_resume_runtime import audit, observe


def _event(raw_fraction: float):
    return json.dumps(
        {
            "targetResources": {
                "hitPoints": int(raw_fraction * 1000000),
                "maxHitPoints": 1000000,
            }
        }
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_fight (
                report_code TEXT, fight_id INTEGER, name TEXT, kill INTEGER,
                difficulty INTEGER, boss_percentage REAL, start_time REAL,
                end_time REAL, encounter_id INTEGER
            );
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                source_is_friendly INTEGER, target_id INTEGER,
                target_instance INTEGER, target_is_friendly INTEGER,
                ability_game_id INTEGER, extra_ability_game_id INTEGER,
                amount REAL, hit_type INTEGER, tick INTEGER,
                cast_track_id INTEGER, resource_change REAL,
                resource_change_type INTEGER, other_resource_change REAL,
                max_resource_amount REAL, waste REAL, overheal REAL,
                absorbed REAL, stack INTEGER, raw_json TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO log_fight VALUES ('R', 7, 'Xalvakka', 1, 121, 0, 0, 120000, 1)"
        )

        rows = []
        fractions = [
            (1000, .75),
            (2000, .705),
            (3000, .699),
            (3500, .695),
            (12000, .700),
            (13000, .68),
            (20000, .45),
            (21000, .405),
            (22000, .399),
            (22500, .395),
            (33000, .400),
            (34000, .38),
        ]
        for index, (timestamp, fraction) in enumerate(fractions):
            rows.append(
                (
                    "R", 7, index, float(timestamp), "damage", 10, 1, 99, 1, 0,
                    1, None, 1000, None, 0, None, None, None, None, None,
                    None, None, None, None, _event(fraction),
                )
            )

        # Smaller hostile target must not be mistaken for Xalvakka.
        rows.append(
            (
                "R", 7, 100, 1500.0, "damage", 10, 1, 55, 1, 0,
                2, None, 500, None, 0, None, None, None, None, None,
                None, None, None, None,
                json.dumps({"targetResources": {"hitPoints": 10000, "maxHitPoints": 10000}}),
            )
        )
        db.executemany(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return path


def test_observes_70_and_40_percent_transition_resume_gaps(tmp_path):
    rows = observe(_database(tmp_path))

    assert [(row.threshold_fraction, row.gap_ms) for row in rows] == [
        (0.70, 8500.0),
        (0.40, 10500.0),
    ]
    assert rows[0].crossing_time_ms == 3000.0
    assert rows[0].gap_start_time_ms == 3500.0
    assert rows[0].resume_time_ms == 12000.0
    assert abs(rows[0].resume_hp_fraction - 0.70) < 1e-9
    assert rows[1].crossing_time_ms == 22000.0
    assert rows[1].resume_time_ms == 33000.0
    assert abs(rows[1].resume_hp_fraction - 0.40) < 1e-9


def test_audit_marks_runtime_observations_as_review_required(tmp_path):
    lines = audit(_database(tmp_path))

    assert any("threshold=70%" in line and "resume=12.000s" in line for line in lines)
    assert any("threshold=40%" in line and "resume=33.000s" in line for line in lines)
    assert lines[-1].startswith("REVIEW_REQUIRED:")


def test_audit_stays_unresolved_without_substantial_transition_gap(tmp_path):
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_fight (
                report_code TEXT, fight_id INTEGER, name TEXT, kill INTEGER,
                difficulty INTEGER, boss_percentage REAL, start_time REAL,
                end_time REAL, encounter_id INTEGER
            );
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                source_is_friendly INTEGER, target_id INTEGER,
                target_instance INTEGER, target_is_friendly INTEGER,
                ability_game_id INTEGER, extra_ability_game_id INTEGER,
                amount REAL, hit_type INTEGER, tick INTEGER,
                cast_track_id INTEGER, resource_change REAL,
                resource_change_type INTEGER, other_resource_change REAL,
                max_resource_amount REAL, waste REAL, overheal REAL,
                absorbed REAL, stack INTEGER, raw_json TEXT
            );
            INSERT INTO log_fight VALUES ('R', 1, 'Xalvakka', 0, 121, 0, 0, 10000, 1);
            """
        )
        for index, (timestamp, fraction) in enumerate(((1000, .71), (2000, .69), (2500, .68), (3000, .67))):
            db.execute(
                "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "R", 1, index, timestamp, "damage", 10, 1, 99, 1, 0,
                    1, None, 10, None, 0, None, None, None, None, None,
                    None, None, None, None, _event(fraction),
                ),
            )

    lines = audit(path)
    assert any(line.startswith("UNRESOLVED:") for line in lines)
