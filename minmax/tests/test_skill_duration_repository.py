from pathlib import Path
import sqlite3

from minmax.skill_duration_repository import SkillDurationRepository


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "duration.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                duration REAL,
                raw_name TEXT
            );
            CREATE TABLE skill_coefficient (
                id INTEGER PRIMARY KEY,
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT
            );
            """
        )
        db.execute("INSERT INTO skill VALUES (1, 100, 'Combat Prayer')")
        db.execute("INSERT INTO ability VALUES (101, 'Combat Prayer')")
        db.execute("INSERT INTO skill_rank VALUES (10, 1, 101, 4, 0, 8.0, 'Combat Prayer')")
        db.execute("INSERT INTO skill_coefficient VALUES (1, 10, 1, '8', 0, 0, 0, 1, NULL)")

        db.execute("INSERT INTO skill VALUES (2, 200, 'Instant Skill')")
        db.execute("INSERT INTO ability VALUES (201, 'Instant Skill')")
        db.execute("INSERT INTO skill_rank VALUES (20, 2, 201, 4, 0, 0.0, 'Instant Skill')")
        db.execute("INSERT INTO skill_coefficient VALUES (2, 20, 1, '8', 0, 0, 0, 1, NULL)")
    return path


def test_resolves_positive_canonical_duration(tmp_path: Path) -> None:
    result = SkillDurationRepository(_database(tmp_path)).resolve_name("Combat Prayer")

    assert result.skill_name == "Combat Prayer"
    assert result.duration_seconds == 8.0
    assert result.ability_id == 101


def test_non_positive_duration_stays_unresolved(tmp_path: Path) -> None:
    result = SkillDurationRepository(_database(tmp_path)).resolve_name("Instant Skill")

    assert result.duration_seconds is None
    assert any("no positive canonical" in item for item in result.unresolved)


def test_unknown_skill_stays_unresolved(tmp_path: Path) -> None:
    result = SkillDurationRepository(_database(tmp_path)).resolve_name("Definitely Missing")

    assert result.duration_seconds is None
    assert result.ability_id is None
    assert result.unresolved
