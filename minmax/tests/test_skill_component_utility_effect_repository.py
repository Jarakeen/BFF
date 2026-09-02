import sqlite3

from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import SkillComponentUtilityEffectRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Their first attack reduces their Movement Speed by 30% for 4 seconds and deals $1 Magic Damage, their second attack immobilizes them for 3 seconds and deals $2 Magic Damage, and their third attack stuns them for 3 seconds and deals $3 Magic Damage.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_keeps_unstable_core_utility_owned_by_each_coefficient(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    repo = SkillComponentUtilityEffectRepository(path)

    first = repo.resolve(10, 1)
    second = repo.resolve(10, 2)
    third = repo.resolve(10, 3)

    assert [item.effect_type for item in first] == [SkillComponentUtilityEffectType.MOVEMENT_SPEED_REDUCTION]
    assert first[0].magnitude_fraction == 0.30
    assert [item.effect_type for item in second] == [SkillComponentUtilityEffectType.IMMOBILIZE]
    assert [item.effect_type for item in third] == [SkillComponentUtilityEffectType.STUN]


def test_repository_does_not_borrow_later_utility_effect(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'Deal $1 Magic Damage, then deal $2 Magic Damage and stun the enemy.'
        );
        """
    )
    db.commit()
    db.close()

    repo = SkillComponentUtilityEffectRepository(path)
    assert repo.resolve(20, 1) == ()
    assert [item.effect_type for item in repo.resolve(20, 2)] == [SkillComponentUtilityEffectType.STUN]


def test_repository_keeps_pragmatic_interrupt_immunity_on_shield_component(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (30, 300);
        INSERT INTO ability VALUES (
            300,
            'Channel a beam dealing $1 Magic Damage every 0.3 seconds, and gain a damage shield that absorbs up to $2 damage and grants interrupt immunity.'
        );
        """
    )
    db.commit()
    db.close()

    repo = SkillComponentUtilityEffectRepository(path)
    assert repo.resolve(30, 1) == ()
    assert [item.effect_type for item in repo.resolve(30, 2)] == [SkillComponentUtilityEffectType.INTERRUPT_IMMUNITY]


def test_repository_fails_closed_when_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()
    assert SkillComponentUtilityEffectRepository(path).resolve(10, 1) == ()
