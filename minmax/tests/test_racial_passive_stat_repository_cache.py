import sqlite3

from minmax.character_progression import CharacterProgression
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
import minmax.racial_passive_stat_repository as module


def _write_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_line TEXT,
                is_passive INTEGER,
                is_player INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                rank INTEGER,
                ability_id INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                description TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, name, skill_line, is_passive, is_player) VALUES (1, 'Syrabane''s Boon', 'High Elf Skills', 1, 1)"
        )
        db.execute(
            "INSERT INTO skill_rank(id, skill_id, rank, ability_id) VALUES (1, 1, 3, 101)"
        )
        db.execute(
            "INSERT INTO ability(ability_id, description) VALUES (101, 'Increases your Max Magicka by 2000')"
        )
        db.commit()


def test_repeated_racial_resolution_reuses_rows_without_reopening_sqlite(tmp_path, monkeypatch) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    repository = RacialPassiveStatRepository(database)
    progression = CharacterProgression(passive_ranks={"Syrabane's Boon": 3})

    original_connect = module.sqlite3.connect
    calls = 0

    def counted_connect(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(module.sqlite3, "connect", counted_connect)

    first = repository.resolve("High Elf", progression)
    second = repository.resolve("High Elf", progression)

    assert first.stats == {"max_magicka": 2000.0}
    assert second.stats == first.stats
    assert calls == 1
