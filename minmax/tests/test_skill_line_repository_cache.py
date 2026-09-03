from __future__ import annotations

import sqlite3

from minmax.skill_line_repository import SkillLineRepository


def _write_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_line TEXT,
                class_type TEXT,
                is_passive INTEGER
            );
            INSERT INTO ability(name, skill_line, class_type, is_passive) VALUES
                ('Combat Prayer', 'Restoring Light', 'Templar', 0),
                ('Combat Prayer', 'Restoration Staff', 'Warden', 0),
                ('Energy Orb', 'Undaunted', NULL, 0);

            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                is_passive INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                rank INTEGER
            );
            INSERT INTO skill(id, name, is_passive) VALUES
                (1, 'Dexterity', 1),
                (2, 'Not Passive', 0);
            INSERT INTO skill_rank(id, skill_id, rank) VALUES
                (10, 1, 1),
                (11, 1, 2),
                (12, 1, 3),
                (20, 2, 4);
            """
        )


def test_skill_line_lookup_cache_matches_sql_trim_and_case_semantics(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name(" Combat Prayer ", class_name="Templar") == "Restoring Light"

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE ability SET skill_line='Changed' WHERE name='Combat Prayer' AND class_type='Templar'"
        )

    assert repository.skill_line_for_ability_name("combat prayer", class_name=" templar ") == "Restoring Light"
    assert repository.skill_line_for_ability_name("Combat Prayer", class_name="Warden") == "Restoration Staff"


def test_internal_whitespace_remains_a_distinct_lookup(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name("Combat   Prayer", class_name="Templar") is None
    assert repository.skill_line_for_ability_name("Combat Prayer", class_name="Templar") == "Restoring Light"


def test_unresolved_skill_line_lookup_is_cached(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name("Missing Skill") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO ability(name, skill_line, class_type, is_passive) VALUES ('Missing Skill', 'Undaunted', NULL, 0)"
        )

    assert repository.skill_line_for_ability_name(" missing skill ") is None
    assert SkillLineRepository(path).skill_line_for_ability_name("Missing Skill") == "Undaunted"


def test_passive_max_rank_lookup_is_cached_per_repository_instance(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.passive_max_rank(" Dexterity ") == 3

    with sqlite3.connect(path) as db:
        db.execute("UPDATE skill_rank SET rank=4 WHERE skill_id=1 AND rank=3")

    assert repository.passive_max_rank("dexterity") == 3
    assert SkillLineRepository(path).passive_max_rank("Dexterity") == 4


def test_unresolved_passive_rank_is_cached(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.passive_max_rank("Missing Passive") is None

    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO skill(id, name, is_passive) VALUES (3, 'Missing Passive', 1)")
        db.execute("INSERT INTO skill_rank(id, skill_id, rank) VALUES (30, 3, 2)")

    assert repository.passive_max_rank(" missing passive ") is None
    assert SkillLineRepository(path).passive_max_rank("Missing Passive") == 2
