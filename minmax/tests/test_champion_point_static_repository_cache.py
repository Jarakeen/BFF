from __future__ import annotations

import sqlite3

from minmax.champion_point_static_repository import ChampionPointStaticRepository


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
