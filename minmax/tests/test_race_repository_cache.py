import sqlite3

from minmax.race_repository import RaceRepository


def _write_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE race (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                alliance TEXT,
                association TEXT
            );
            CREATE TABLE race_stat (
                id INTEGER PRIMARY KEY,
                race_id INTEGER NOT NULL,
                stat TEXT NOT NULL,
                value REAL NOT NULL
            );
            INSERT INTO race(id, name, alliance, association)
            VALUES (1, 'Altmer', 'Aldmeri Dominion', 'Summerset');
            INSERT INTO race_stat(id, race_id, stat, value)
            VALUES (10, 1, 'max_magicka', 2000.0);
            """
        )


def test_race_stat_map_is_cached_for_repository_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = RaceRepository(path)

    first = repository.get_stat_map_by_name("Altmer")
    assert first == {"max_magicka": 2000.0}

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE race_stat SET value=2500.0 WHERE race_id=1 AND stat='max_magicka'"
        )

    assert repository.get_stat_map_by_name("Altmer") == {"max_magicka": 2000.0}
    assert RaceRepository(path).get_stat_map_by_name("Altmer") == {"max_magicka": 2500.0}


def test_cached_race_results_are_returned_as_fresh_containers(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = RaceRepository(path)

    stats = repository.get_stats(1)
    stat_map = repository.get_stat_map(1)
    stats.clear()
    stat_map["max_magicka"] = -1.0

    assert len(repository.get_stats(1)) == 1
    assert repository.get_stat_map(1) == {"max_magicka": 2000.0}


def test_missing_race_is_cached_for_repository_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = RaceRepository(path)

    assert repository.get_race("Bosmer") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO race(id, name, alliance, association) VALUES (2, 'Bosmer', '', '')"
        )

    assert repository.get_race("Bosmer") is None
    assert RaceRepository(path).get_race("Bosmer") is not None
