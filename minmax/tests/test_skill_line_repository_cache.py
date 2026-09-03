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
            """
        )


def test_skill_line_lookup_cache_normalizes_name_and_class(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name(" Combat   Prayer ", class_name="Templar") == "Restoring Light"

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE ability SET skill_line='Changed' WHERE name='Combat Prayer' AND class_type='Templar'"
        )

    assert repository.skill_line_for_ability_name("combat prayer", class_name=" templar ") == "Restoring Light"
    assert repository.skill_line_for_ability_name("Combat Prayer", class_name="Warden") == "Restoration Staff"


def test_unresolved_skill_line_lookup_is_cached(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name("Missing Skill") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO ability(name, skill_line, class_type, is_passive) VALUES ('Missing Skill', 'Undaunted', NULL, 0)"
        )

    assert repository.skill_line_for_ability_name(" missing   skill ") is None
    assert SkillLineRepository(path).skill_line_for_ability_name("Missing Skill") == "Undaunted"
