import sqlite3

from minmax.skill_component_missing_health_healing_repository import (
    SkillComponentMissingHealthHealingRepository,
)


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            coef_description TEXT
        );
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Deal $1 Magic Damage and heal you for 25% of your missing Health every 1 second for 3 seconds.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_missing_health_secondary_heal(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = SkillComponentMissingHealthHealingRepository(path).resolve(10, 1)

    assert len(rows) == 1
    assert rows[0].fraction == 0.25


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentMissingHealthHealingRepository(path).resolve(999, 1) == ()


def test_repository_does_not_attach_to_missing_neighbor_component(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentMissingHealthHealingRepository(path).resolve(10, 2) == ()


def test_repository_requires_damage_component_identity(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'Heal yourself for $1 Health and heal for 25% of your missing Health.'
        );
        """
    )
    db.commit()
    db.close()

    assert SkillComponentMissingHealthHealingRepository(path).resolve(20, 1) == ()
