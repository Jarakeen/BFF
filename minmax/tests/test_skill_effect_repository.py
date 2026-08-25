import sqlite3

from minmax.skill_effect_repository import SkillEffectRepository
from minmax.character_build.character_class import CharacterClass


def make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            target TEXT,
            duration REAL,
            class_type TEXT,
            skill_line TEXT,
            base_ability_id INTEGER,
            rank INTEGER,
            morph INTEGER,
            is_passive INTEGER DEFAULT 0,
            is_player INTEGER DEFAULT 1,
            is_crafted INTEGER DEFAULT 0
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
        INSERT INTO ability VALUES
            (101, 'Test Courage', 'Group', 12000.0, 'Warden', 'Green Balance', 101, 1, 0, 0, 1, 0),
            (102, 'Test Courage', 'Group', 12000.0, 'Warden', 'Green Balance', 101, 2, 0, 0, 1, 0),
            (103, 'Morph Courage', 'Group', 12000.0, 'Warden', 'Green Balance', 101, 1, 1, 0, 1, 0),
            (104, 'Morph Courage', 'Group', 12000.0, 'Warden', 'Green Balance', 101, 2, 1, 0, 1, 0),
            (105, 'Other Class', 'Group', 12000.0, 'Sorcerer', 'Green Balance', 105, 1, 0, 0, 1, 0),
            (106, 'Passive Courage', 'Group', 12000.0, 'Warden', 'Green Balance', 106, 1, 0, 1, 1, 0),
            (107, 'Hireling', 'Group', 12000.0, '', 'Woodworking', 107, 1, 0, 0, 1, 1);
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
    assert effects[0].duration == 12000.0


def test_skill_repository_does_not_invent_missing_linkage(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)

    repo = SkillEffectRepository(db)

    assert repo.resolve(999) == ()


def test_available_skills_are_class_only_and_collapse_ranks(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)

    repo = SkillEffectRepository(db)
    skills = repo.available_skills(CharacterClass.WARDEN)

    assert skills == ((101, 'Test Courage'), (103, 'Morph Courage'))
    assert all(name not in {'Other Class', 'Passive Courage', 'Hireling'} for _, name in skills)
