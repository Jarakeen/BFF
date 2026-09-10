import sqlite3

from services.combat_effect_reference_service import CombatEffectReferenceService


def _create_effect_tables(path):
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE combat_effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT,
                duration REAL,
                tick_interval REAL,
                stack_max INTEGER,
                immunity_duration REAL,
                raw_source TEXT
            );
            CREATE TABLE combat_effect_trigger (
                id INTEGER PRIMARY KEY,
                combat_effect_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                damage_type TEXT,
                weapon_requirement TEXT,
                condition TEXT,
                raw_source TEXT
            );
            CREATE TABLE combat_effect_interaction (
                id INTEGER PRIMARY KEY,
                source_effect_id INTEGER NOT NULL,
                target_name TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                condition TEXT,
                duration REAL,
                target_value REAL,
                target_unit TEXT,
                target_scope TEXT,
                raw_source TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO combat_effect VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "Chilled", "Status", "Frost status.", 4.0, None, None, None, "raw"),
        )
        connection.execute(
            "INSERT INTO combat_effect_trigger VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "Damage", "Frost", None, None, "trigger source"),
        )
        connection.execute(
            "INSERT INTO combat_effect_interaction VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "Minor Maim", "Applies", None, 4.0, 5.0, "percent", "Target", "interaction source"),
        )
        connection.commit()
    finally:
        connection.close()


def test_reference_service_reads_effect_triggers_and_interactions_without_writing(tmp_path):
    database = tmp_path / "eso.db"
    _create_effect_tables(database)
    before = database.read_bytes()

    effects = CombatEffectReferenceService(database).all()

    assert len(effects) == 1
    effect = effects[0]
    assert effect.name == "Chilled"
    assert effect.duration == 4.0
    assert effect.triggers[0].damage_type == "Frost"
    assert effect.interactions[0].target_name == "Minor Maim"
    assert effect.interactions[0].target_value == 5.0
    assert database.read_bytes() == before


def test_reference_service_returns_empty_for_missing_database_or_table(tmp_path):
    assert CombatEffectReferenceService(tmp_path / "missing.db").all() == ()

    database = tmp_path / "empty.db"
    sqlite3.connect(database).close()
    assert CombatEffectReferenceService(database).all() == ()
