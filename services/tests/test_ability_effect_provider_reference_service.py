import sqlite3

from services.ability_effect_provider_reference_service import (
    AbilityEffectProviderReferenceService,
)


def _db(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE ability (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER,
            name TEXT,
            index_name TEXT
        );
        CREATE TABLE combat_effect (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE ability_combat_effect (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            combat_effect_id INTEGER NOT NULL,
            relationship TEXT NOT NULL,
            weapon_type TEXT,
            condition TEXT,
            source TEXT,
            confidence TEXT
        );
        """
    )
    db.executemany(
        "INSERT INTO ability(id, ability_id, name, index_name) VALUES (?, ?, ?, ?)",
        (
            (1, 1001, "Aggressive Horn", "aggressive_horn"),
            (2, 1002, "Aggressive Horn", "aggressive_horn"),
            (3, 1003, "Wall of Elements", "wall_of_elements"),
        ),
    )
    db.executemany(
        "INSERT INTO combat_effect(id, name) VALUES (?, ?)",
        ((10, "Major Force"), (11, "Chilled")),
    )
    db.executemany(
        """INSERT INTO ability_combat_effect(
            id, ability_id, combat_effect_id, relationship, weapon_type,
            condition, source, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            (20, 1, 10, "Grants", None, None, "ESO-Hub", "explicit"),
            (21, 2, 10, "Grants", None, None, "ESO-Hub", "explicit"),
            (22, 3, 11, "Applies", "Ice Staff", None, "ESO Wiki", "explicit"),
        ),
    )
    db.commit()
    db.close()
    return path


def test_reader_uses_canonical_skill_key_and_collapses_numeric_alias_rows(tmp_path):
    rows = AbilityEffectProviderReferenceService(_db(tmp_path)).for_effect("Major Force")

    assert len(rows) == 1
    assert rows[0].ability_key == "aggressive_horn"
    assert rows[0].ability_name == "Aggressive Horn"
    assert rows[0].effect_name == "Major Force"
    assert rows[0].relationship == "Grants"
    assert rows[0].source == "ESO-Hub"


def test_reader_preserves_reviewed_conditions_without_inference(tmp_path):
    rows = AbilityEffectProviderReferenceService(_db(tmp_path)).for_effect("chilled")

    assert len(rows) == 1
    assert rows[0].ability_key == "wall_of_elements"
    assert rows[0].weapon_type == "Ice Staff"
    assert rows[0].condition is None
    assert rows[0].confidence == "explicit"


def test_reader_returns_empty_when_required_tables_are_missing(tmp_path):
    path = tmp_path / "empty.db"
    sqlite3.connect(path).close()

    assert AbilityEffectProviderReferenceService(path).all() == ()
