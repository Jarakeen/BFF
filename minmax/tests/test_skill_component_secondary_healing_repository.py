import sqlite3

from minmax.skill_component_secondary_healing_repository import SkillComponentSecondaryHealingRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Deal $1 Magic Damage and heal for 45% of the damage caused.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_damage_linked_healing(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    rows = SkillComponentSecondaryHealingRepository(path).resolve(10, 1)
    assert len(rows) == 1
    assert rows[0].fraction == 0.45


def test_repository_requires_damage_component(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (100, 'Heal for $1 Health and heal for 50% of damage dealt.');
        """
    )
    db.commit()
    db.close()
    assert SkillComponentSecondaryHealingRepository(path).resolve(10, 1) == ()
