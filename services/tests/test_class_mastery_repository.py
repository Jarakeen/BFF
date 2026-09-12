from __future__ import annotations

import sqlite3

import services.class_mastery_repository as mastery_module
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


def test_repository_caches_mastery_catalog_per_instance(monkeypatch, tmp_path):
    database = _database(tmp_path)
    original_connect = mastery_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(mastery_module.sqlite3, "connect", counting_connect)
    repository = ClassMasteryRepository(database)

    first = repository.all()
    second = repository.all()
    sorcerer = repository.for_class("Sorcerer")
    sorcerer_again = repository.for_class("sOrCeReR")

    assert second is first
    assert sorcerer_again is sorcerer
    assert [row.name for row in sorcerer] == ["Font of Power"]
    assert connect_count == 1

    # A new repository still observes a later database change; the cache is not
    # process-global and cannot hide updated canonical data from a fresh reader.
    with original_connect(database) as db:
        db.execute(
            "INSERT INTO skill VALUES (?, ?, ?, ?, ?, ?, ?)",
            (5, 1005, "Fresh Mastery", "Sorcerer", "Class Mastery", "New row.", 1),
        )

    fresh_repository = ClassMasteryRepository(database)
    assert [row.name for row in fresh_repository.for_class("Sorcerer")] == [
        "Font of Power",
        "Fresh Mastery",
    ]
    assert connect_count == 2
