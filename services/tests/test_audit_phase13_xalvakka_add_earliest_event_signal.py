import sqlite3
from pathlib import Path

from tools.audit_phase13_xalvakka_add_earliest_event_signal import audit, observe


def _database(path: Path) -> Path:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE log_report_actor (
            report_code TEXT NOT NULL,
            actor_id INTEGER NOT NULL,
            game_id INTEGER,
            name TEXT,
            actor_type TEXT,
            actor_subtype TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (report_code, actor_id)
        );
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
            raw_json TEXT NOT NULL,
            PRIMARY KEY (report_code, fight_id)
        );
        CREATE TABLE log_event (
            report_code TEXT NOT NULL,
            fight_id INTEGER NOT NULL,
            event_index INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
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
            raw_json TEXT NOT NULL,
            PRIMARY KEY (report_code, fight_id, event_index)
        );
        """
    )
    db.execute(
        "INSERT INTO log_report_actor VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("R", 104, 101465, "Iron Atronach", "NPC", "NPC", "{}"),
    )
    db.execute(
        "INSERT INTO log_fight VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("R", 1, "Xalvakka", 1, None, None, 100000.0, 200000.0, None, "{}"),
    )
    rows = (
        (0, 110000.0, "begincast", 104, 0, 1, 0, 0, '{"sourceInstance":1}'),
        (1, 111000.0, "damage", 104, 0, 1, 0, 50, '{"sourceInstance":1}'),
        (2, 113000.0, "damage", 1, 1, 104, 1, 100, '{"targetInstance":1}'),
    )
    for index, timestamp, event_type, source_id, source_friendly, target_id, target_instance, amount, raw_json in rows:
        db.execute(
            """
            INSERT INTO log_event (
                report_code, fight_id, event_index, timestamp, event_type,
                source_id, source_is_friendly, target_id, target_instance,
                target_is_friendly, amount, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "R", 1, index, timestamp, event_type, source_id, source_friendly,
                target_id, target_instance, 0 if target_id == 104 else 1, amount, raw_json,
            ),
        )
    db.commit()
    db.close()
    return path


def test_observe_uses_earliest_source_cast_before_first_friendly_damage(tmp_path):
    row = observe(_database(tmp_path / "runtime.db"))[0]

    assert row.actor_name == "Iron Atronach"
    assert row.instance_id == 1
    assert row.first_involving_ms == 110000.0
    assert row.first_source_ms == 110000.0
    assert row.first_cast_ms == 110000.0
    assert row.first_friendly_damage_ms == 113000.0
    assert row.cast_to_damage_ms == 3000.0


def test_audit_reports_signal_coverage_without_promoting_spawn_truth(tmp_path):
    lines = audit(_database(tmp_path / "runtime.db"))
    text = "\n".join(lines)

    assert "ADD_SIGNAL:" in text
    assert "cast_to_damage=3.000s" in text
    assert "SIGNAL_COVERAGE: actor=Iron Atronach instances=1" in text
    assert "observational activity evidence" in text
