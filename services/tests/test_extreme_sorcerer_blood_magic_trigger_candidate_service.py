from pathlib import Path
import sqlite3

from services.extreme_sorcerer_blood_magic_trigger_candidate_service import (
    ExtremeSorcererBloodMagicTriggerCandidateService,
)


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (id INTEGER PRIMARY KEY, name TEXT, is_passive INTEGER);
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                rank INTEGER,
                morph INTEGER,
                raw_name TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                skill_line TEXT,
                base_cost REAL,
                base_mechanic INTEGER,
                is_player INTEGER,
                is_passive INTEGER
            );
            """
        )
        db.executemany(
            "INSERT INTO skill(id, name, is_passive) VALUES (?, ?, ?)",
            [(1, "Dark Cast", 0), (2, "Free Dark Cast", 0), (3, "Other Cast", 0)],
        )
        db.executemany(
            "INSERT INTO skill_rank(id, skill_id, ability_id, rank, morph, raw_name) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (10, 1, 100, 1, 0, "Dark Cast"),
                (11, 1, 101, 4, 0, "Dark Cast"),
                (20, 2, 200, 4, 0, "Free Dark Cast"),
                (30, 3, 300, 4, 0, "Other Cast"),
            ],
        )
        db.executemany(
            "INSERT INTO ability(ability_id, name, skill_line, base_cost, base_mechanic, is_player, is_passive) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (100, "Dark Cast", "Dark Magic", 1000, 0, 1, 0),
                (101, "Dark Cast", "Dark Magic", 2000, 0, 1, 0),
                (200, "Free Dark Cast", "Dark Magic", 0, 0, 1, 0),
                (300, "Other Cast", "Daedric Summoning", 2000, 0, 1, 0),
            ],
        )


def test_trigger_catalog_requires_positive_cost_dark_magic_and_selects_max_rank(tmp_path):
    database = tmp_path / "eso.db"
    _database(database)

    rows = ExtremeSorcererBloodMagicTriggerCandidateService(database).candidates()

    assert len(rows) == 1
    row = rows[0]
    assert row.name == "Dark Cast"
    assert row.ability_id == 101
    assert row.skill_rank_id == 11
    assert row.rank == 4
    assert row.base_cost == 2000.0
    assert row.skill_line == "Dark Magic"


def test_trigger_catalog_fails_closed_when_database_is_missing(tmp_path):
    missing = tmp_path / "missing.db"
    service = ExtremeSorcererBloodMagicTriggerCandidateService(missing)

    try:
        service.candidates()
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("missing canonical database must fail closed")
