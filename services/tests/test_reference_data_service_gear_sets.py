from __future__ import annotations

import sqlite3

from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService


def test_gear_set_picker_unions_legacy_and_canonical_entities(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT NOT NULL
            );
            """
        )
        db.execute("INSERT INTO gear_set(id, name) VALUES (1, 'Master Architect')")
        db.execute("INSERT INTO gear_set(id, name) VALUES (2, 'Duplicate Set')")
        db.execute(
            "INSERT INTO entity(id, entity_type, name, slug) VALUES (?, ?, ?, ?)",
            ('gear_set:puncturing_remedy', 'gear_set', 'Puncturing Remedy', 'puncturing-remedy'),
        )
        db.execute(
            "INSERT INTO entity(id, entity_type, name, slug) VALUES (?, ?, ?, ?)",
            ('gear_set:duplicate_set', 'gear_set', 'Duplicate Set', 'duplicate-set'),
        )
        db.execute(
            "INSERT INTO entity(id, entity_type, name, slug) VALUES (?, ?, ?, ?)",
            ('food:not_a_set', 'food', 'Not A Set', 'not-a-set'),
        )
        db.commit()

    reference = ReferenceDataService(EsoDatabase(path))

    assert reference.list_gear_set_names() == [
        'Duplicate Set',
        'Master Architect',
        'Puncturing Remedy',
    ]


def test_gear_set_picker_falls_back_when_canonical_entity_table_is_absent(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        db.execute("INSERT INTO gear_set(id, name) VALUES (1, 'Serpent\'s Disdain')")
        db.commit()

    reference = ReferenceDataService(EsoDatabase(path))

    assert reference.list_gear_set_names() == ["Serpent's Disdain"]
