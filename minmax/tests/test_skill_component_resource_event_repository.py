import sqlite3

from minmax.skill_component_resource_event import SkillComponentResourceType
from minmax.skill_component_resource_event_repository import SkillComponentResourceEventRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (100, 'Deal $1 Magic Damage. Restore $2 Magicka.');
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_explicit_magicka_restore(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    events = SkillComponentResourceEventRepository(path).resolve(10, 2)

    assert len(events) == 1
    assert events[0].resource_type is SkillComponentResourceType.MAGICKA


def test_repository_does_not_borrow_other_component_resource_text(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentResourceEventRepository(path).resolve(10, 1) == ()


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentResourceEventRepository(path).resolve(999, 2) == ()


def test_repository_fails_closed_when_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    assert SkillComponentResourceEventRepository(path).resolve(10, 1) == ()
