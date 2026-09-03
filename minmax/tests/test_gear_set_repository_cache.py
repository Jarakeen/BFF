from __future__ import annotations

import sqlite3

from minmax.gear_set_repository import GearSetRepository


def _write_db(path) -> None:
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
            INSERT INTO gear_set(id, name, category, max_equip_count)
            VALUES (1, 'Spell Power Cure', 'Dungeon', 5);
            INSERT INTO gear_set_bonus(id, set_id, piece_count, description) VALUES
                (10, 1, 2, 'Adds Magicka'),
                (11, 1, 5, 'Grants Major Courage');
            """
        )


def test_set_name_lookup_is_cached_and_populates_id_cache(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = GearSetRepository(path)

    first = repository.get_set("Spell Power Cure")
    assert first is not None
    assert first.id == 1

    with sqlite3.connect(path) as db:
        db.execute("UPDATE gear_set SET name='Changed' WHERE id=1")

    assert repository.get_set("Spell Power Cure") == first
    assert repository.get_set_by_id(1) == first
    assert GearSetRepository(path).get_set_by_id(1).name == "Changed"


def test_bonus_lookup_is_cached_and_returns_fresh_lists(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = GearSetRepository(path)

    first = repository.get_bonuses(1)
    assert [bonus.piece_count for bonus in first] == [2, 5]

    first.clear()
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM gear_set_bonus WHERE set_id=1")

    second = repository.get_bonuses(1)
    assert [bonus.piece_count for bonus in second] == [2, 5]
    assert second is not first
    assert GearSetRepository(path).get_bonuses(1) == []


def test_missing_set_name_is_cached(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = GearSetRepository(path)

    assert repository.get_set("Missing Set") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (2, 'Missing Set', 'Trial', 5)"
        )

    assert repository.get_set("Missing Set") is None
    assert GearSetRepository(path).get_set("Missing Set") is not None
