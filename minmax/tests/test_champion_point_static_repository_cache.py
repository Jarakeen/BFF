from __future__ import annotations

import sqlite3

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE,
    ChampionPointStaticRepository,
)


def _write_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            INSERT INTO champion_point(
                id, name, skill_type, max_points, jump_points,
                min_description, max_description, description
            ) VALUES (
                1, 'Boundless Vitality', 0, 50, '10,20,30,40,50',
                NULL, 'Grants 28 Max Health per stage.', NULL
            );
            """
        )


def test_static_champion_point_record_is_cached_for_repository_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = ChampionPointStaticRepository(path)

    first = repository.get(" Boundless Vitality ")
    assert first is not None
    assert first.max_points == 50

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE champion_point SET max_points=99 WHERE name='Boundless Vitality'"
        )

    second = repository.get("Boundless Vitality")
    fresh = ChampionPointStaticRepository(path).get("Boundless Vitality")

    assert second == first
    assert fresh is not None
    assert fresh.max_points == 99


def test_missing_static_champion_point_record_is_cached(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = ChampionPointStaticRepository(path)

    assert repository.get("Missing Star") is None

    with sqlite3.connect(path) as db:
        db.execute(
            """
            INSERT INTO champion_point(
                id, name, skill_type, max_points, jump_points,
                min_description, max_description, description
            ) VALUES (
                2, 'Missing Star', 0, 10, '10',
                NULL, 'Grants 100 Armor per stage.', NULL
            )
            """
        )

    assert repository.get("Missing Star") is None
    assert ChampionPointStaticRepository(path).get("Missing Star") is not None


class _CountingRepository(ChampionPointStaticRepository):
    def __init__(self, database_path) -> None:
        super().__init__(database_path)
        self.connect_calls = 0

    def _connect(self):
        self.connect_calls += 1
        return super()._connect()


def test_catalog_enumeration_populates_get_cache_for_resolve(tmp_path) -> None:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            f"""
            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            INSERT INTO champion_point(
                id, name, skill_type, max_points, jump_points,
                min_description, max_description, description
            ) VALUES (
                1, 'Eldritch Insight', {CHAMPION_SKILL_TYPE_NORMAL}, 20, '',
                NULL, NULL, 'Grants 26 Max Magicka per stage.'
            );
            """
        )

    repository = _CountingRepository(path)
    records = repository.non_slottable_records()

    assert repository.connect_calls == 1
    assert [row.name for row in records] == ["Eldritch Insight"]

    effects, unresolved = repository.resolve("Eldritch Insight", 20)

    assert repository.connect_calls == 1
    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].value == 520.0


def test_catalog_lists_are_cached_and_shared_with_get(tmp_path) -> None:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            f"""
            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            INSERT INTO champion_point VALUES (
                1, 'Eldritch Insight', {CHAMPION_SKILL_TYPE_NORMAL}, 20, '',
                NULL, NULL, 'Grants 26 Max Magicka per stage.'
            );
            INSERT INTO champion_point VALUES (
                2, 'Arcane Supremacy', {CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE}, 50, '',
                NULL, NULL, 'fixture'
            );
            """
        )

    repository = _CountingRepository(path)
    first_non_slottable = repository.non_slottable_records()
    first_slottable = repository.slottable_records()
    assert repository.connect_calls == 2

    second_non_slottable = repository.non_slottable_records()
    second_slottable = repository.slottable_records()
    assert repository.connect_calls == 2
    assert second_non_slottable is first_non_slottable
    assert second_slottable is first_slottable

    assert repository.get("Eldritch Insight") is first_non_slottable[0]
    assert repository.get("Arcane Supremacy") is first_slottable[0]
    assert repository.connect_calls == 2
