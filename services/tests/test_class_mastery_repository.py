from __future__ import annotations

import sqlite3

from services.class_mastery_repository import ClassMasteryRepository


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                class_type TEXT,
                skill_line TEXT,
                description TEXT,
                is_passive INTEGER
            )
            """
        )
        db.executemany(
            "INSERT INTO skill VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (1, 1001, "Font of Power", "Sorcerer", "Class Mastery", "Gain |cffffff333|r Weapon and Spell Damage.", 1),
                (2, 1002, "Above and Beyond", "Nightblade", "Class Mastery", "Gain |cffffff25|r% Critical Damage.", 1),
                (3, 1003, "Magicka Mastery", "", "Breton Skills", "Reduces Magicka costs by |cffffff2|r%.", 1),
                (4, 1004, "Not Passive", "Sorcerer", "Class Mastery", "Nope.", 0),
            ),
        )
    return path


def test_repository_reads_only_exact_class_mastery_passives(tmp_path):
    rows = ClassMasteryRepository(_database(tmp_path)).all()

    assert [row.name for row in rows] == ["Above and Beyond", "Font of Power"]
    assert all("|c" not in row.description and "|r" not in row.description for row in rows)


def test_repository_filters_by_class_case_insensitively(tmp_path):
    rows = ClassMasteryRepository(_database(tmp_path)).for_class("sOrCeReR")

    assert len(rows) == 1
    assert rows[0].name == "Font of Power"
    assert rows[0].description == "Gain 333 Weapon and Spell Damage."
