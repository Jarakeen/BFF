import sqlite3

from minmax.skill_component_resource_event import (
    SkillComponentResourceAmountBasis,
    SkillComponentResourceScalingDriver,
    SkillComponentResourceType,
)
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


def test_repository_links_current_restore_to_bounded_resource_rule_context(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'You also restore 12% Stamina, increasing by up to 100% based on how high your current Health is Current Restore: $2 While slotted you gain Major Vitality.'
        );
        """
    )
    db.commit()
    db.close()

    events = SkillComponentResourceEventRepository(path).resolve(20, 2)

    assert len(events) == 1
    event = events[0]
    assert event.resource_type is SkillComponentResourceType.STAMINA
    assert event.amount_basis is SkillComponentResourceAmountBasis.PERCENT_RESOURCE
    assert event.amount_fraction == 0.12
    assert event.max_bonus_fraction == 1.0
    assert event.scaling_driver is SkillComponentResourceScalingDriver.CURRENT_HEALTH


def test_current_restore_window_does_not_borrow_earlier_unrelated_resource_sentence(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (30, 300);
        INSERT INTO ability VALUES (
            300,
            'Restore 20% Magicka. Gain Major Resolve. Current Restore: $2 While slotted you gain Major Vitality.'
        );
        """
    )
    db.commit()
    db.close()

    assert SkillComponentResourceEventRepository(path).resolve(30, 2) == ()


def test_current_restore_window_requires_current_health_scaling_evidence(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (40, 400);
        INSERT INTO ability VALUES (
            400,
            'Restore 12% Stamina when the effect ends Current Restore: $2 While slotted you gain Major Vitality.'
        );
        """
    )
    db.commit()
    db.close()

    assert SkillComponentResourceEventRepository(path).resolve(40, 2) == ()


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentResourceEventRepository(path).resolve(999, 2) == ()


def test_repository_fails_closed_when_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    assert SkillComponentResourceEventRepository(path).resolve(10, 1) == ()
