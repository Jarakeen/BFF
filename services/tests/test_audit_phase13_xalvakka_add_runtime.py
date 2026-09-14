from pathlib import Path
import sqlite3

from tools.audit_phase13_xalvakka_add_runtime import audit


def test_add_runtime_audit_reports_named_instances_without_promoting_spawn_timing(tmp_path: Path):
    database = tmp_path / "runtime.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE log_fight (
            report_code TEXT,
            fight_id INTEGER,
            name TEXT,
            kill INTEGER,
            start_time REAL,
            end_time REAL
        );
        CREATE TABLE log_report_actor (
            report_code TEXT,
            actor_id INTEGER,
            game_id INTEGER,
            name TEXT,
            actor_type TEXT,
            actor_subtype TEXT,
            pet_owner_id INTEGER,
            raw_json TEXT
        );
        CREATE TABLE log_event (
            report_code TEXT,
            fight_id INTEGER,
            timestamp REAL,
            event_type TEXT,
            source_is_friendly INTEGER,
            target_is_friendly INTEGER,
            target_id INTEGER,
            target_instance INTEGER,
            amount REAL,
            raw_json TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO log_fight VALUES ('R', 31, 'Xalvakka', 1, 1000, 101000)"
    )
    connection.executemany(
        "INSERT INTO log_report_actor VALUES (?, ?, ?, ?, ?, ?, NULL, '{}')",
        (
            ("R", 10, 10010, "Iron Atronach", "NPC", "NPC"),
            ("R", 11, 10011, "Daedroth", "NPC", "NPC"),
        ),
    )
    connection.executemany(
        "INSERT INTO log_event VALUES (?, ?, ?, 'damage', 1, 0, ?, ?, ?, ?)",
        (
            ("R", 31, 11000, 10, 1, 50, '{"targetResources":{"maxHitPoints":5000000}}'),
            ("R", 31, 15000, 10, 1, 75, '{"targetResources":{"maxHitPoints":5000000}}'),
            ("R", 31, 21000, 11, 2, 90, '{"targetResources":{"maxHitPoints":3000000}}'),
        ),
    )
    connection.commit()
    connection.close()

    lines = audit(database)

    assert any("Iron Atronach#1" in line and "first_damage=10.000s" in line for line in lines)
    assert any("Daedroth#1" in line and "first_damage=20.000s" in line for line in lines)
    assert lines[-2] == "OBSERVED_ADD_INSTANCES=2"
    assert "not reviewed spawn/taunt timing" in lines[-1]
