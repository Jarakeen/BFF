import sqlite3

from minmax.skill_effect_repository import SkillEffectRepository


def make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            target TEXT,
            is_player INTEGER DEFAULT 1
        );
        CREATE TABLE effect (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        );
        CREATE TABLE effect_variant (
            id INTEGER PRIMARY KEY,
            effect_id INTEGER NOT NULL,
            type TEXT,
            description TEXT
        );
        CREATE TABLE effect_source (
            id INTEGER PRIMARY KEY,
            effect_variant_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            condition TEXT
        );
        CREATE TABLE ability_effect_link (
            id INTEGER PRIMARY KEY,
            effect_source_id INTEGER NOT NULL,
            effect_variant_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            condition TEXT,
            match_method TEXT NOT NULL,
            confidence REAL NOT NULL
        );
        INSERT INTO ability VALUES (101, 'Test Courage', 'Group', 1);
        INSERT INTO effect VALUES (201, 'major_courage', 'buff');
        INSERT INTO effect_variant VALUES (301, 201, 'Major', 'test');
        INSERT INTO effect_source VALUES (401, 301, 'Abilities', 'Test Courage', NULL);
        INSERT INTO ability_effect_link VALUES (501, 401, 301, 101, NULL, 'exact_name', 1.0);
        """
    )
    db.commit()
    db.close()


def test_skill_repository_resolves_linked_effect(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)

    repo = SkillEffectRepository(db)
    effects = repo.resolve(101)

    assert len(effects) == 1
    assert effects[0].name == 'major_courage'
    assert effects[0].source == 'Test Courage'
    assert effects[0].layer.value == 'cast'
    assert effects[0].category.value == 'buff'
    assert effects[0].target_type.value == 'group'


def test_skill_repository_does_not_invent_missing_linkage(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)

    repo = SkillEffectRepository(db)

    assert repo.resolve(999) == ()
