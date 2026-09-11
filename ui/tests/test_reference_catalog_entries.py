import sqlite3
from pathlib import Path

from ui.reference_catalog_entries import build_player_catalog_reference_entries


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            INSERT INTO gear_set VALUES (10, 'Field Test Set', 'Dungeon', 5);
            INSERT INTO gear_set_bonus VALUES (1, 10, 2, 'Adds 100 Magicka Recovery.');
            INSERT INTO gear_set_bonus VALUES (2, 10, 5, 'Gain 500 Weapon and Spell Damage.');

            CREATE TABLE skill (
                id TEXT PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,
                class_type TEXT,
                skill_line TEXT,
                target TEXT,
                skill_type TEXT,
                is_passive INTEGER,
                is_player INTEGER,
                is_crafted INTEGER,
                crafted_id INTEGER
            );
            CREATE TABLE skill_rank (
                skill_id TEXT,
                ability_id INTEGER,
                display_id INTEGER,
                rank INTEGER,
                morph INTEGER,
                skill_index INTEGER,
                learned_level INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,
                target TEXT,
                skill_type TEXT,
                base_mechanic TEXT,
                cost INTEGER,
                buff_type TEXT
            );

            INSERT INTO skill VALUES (
                'combat_prayer', 100, 'Blessing of Protection', '', 'Base tooltip', '',
                '', 'Restoration Staff', 'Cone', 'Active', 0, 1, 0, NULL
            );
            INSERT INTO skill_rank VALUES ('combat_prayer', 101, 101, 4, 1, 1, 1);
            INSERT INTO ability VALUES (
                101, 100, 'Combat Prayer', '', 'Heal allies and empower them.', '',
                'Cone', 'Active', 'Magicka', 3510, ''
            );

            INSERT INTO skill VALUES (
                'essence_drain', 200, 'Essence Drain', '', 'Restoration passive.', '',
                '', 'Restoration Staff', 'Self', 'Passive', 1, 1, 0, NULL
            );
            INSERT INTO skill_rank VALUES ('essence_drain', 201, 201, 2, 0, 2, 1);
            INSERT INTO ability VALUES (
                201, 200, 'Essence Drain', '', 'Heavy attacks grant a bonus.', '',
                'Self', 'Passive', '', 0, ''
            );

            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                discipline_id INTEGER,
                description TEXT,
                min_description TEXT,
                max_description TEXT,
                max_points INTEGER,
                jump_points TEXT,
                skill_type TEXT
            );
            INSERT INTO champion_point VALUES (
                300, 'Fighting Finesse', 1, 'Increases critical damage and healing.', '', '', 50, '', 'Slottable'
            );
            """
        )


def test_reference_catalog_adds_gear_skills_passives_and_cp(tmp_path: Path):
    path = tmp_path / "eso.db"
    _database(path)

    entries = build_player_catalog_reference_entries(path)
    by_name = {entry.name: entry for entry in entries}

    assert by_name["Field Test Set"].entry_type == "Gear Set"
    assert any(label == "5-piece bonus" for label, _value in by_name["Field Test Set"].details)

    skill = by_name["Combat Prayer — Restoration Staff"]
    assert skill.entry_type == "Skill"
    assert "empower" in skill.summary.casefold()

    passive = by_name["Essence Drain — Restoration Staff"]
    assert passive.entry_type == "Passive"

    cp = by_name["Fighting Finesse"]
    assert cp.entry_type == "Champion Point"


def test_history_language_is_explicitly_non_mechanical(tmp_path: Path):
    path = tmp_path / "eso.db"
    _database(path)

    entries = build_player_catalog_reference_entries(path)
    field_test = next(entry for entry in entries if entry.name == "Field Test Set")

    assert "never feed combat calculations" in field_test.field_note.casefold()
