import sqlite3

import pytest

from models.build_model import PlayerBuild
from services.build_math_service import BuildMathService


def make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            base_ability_id INTEGER NOT NULL UNIQUE,
            name TEXT,
            index_name TEXT,
            description TEXT,
            texture TEXT,
            class_type INTEGER,
            skill_line INTEGER,
            target INTEGER,
            skill_type INTEGER,
            is_passive INTEGER NOT NULL DEFAULT 0,
            is_player INTEGER NOT NULL DEFAULT 0,
            is_crafted INTEGER NOT NULL DEFAULT 0,
            crafted_id INTEGER
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL UNIQUE,
            display_id INTEGER,
            rank INTEGER,
            morph INTEGER,
            prev_skill INTEGER,
            next_skill INTEGER,
            next_skill2 INTEGER,
            skill_index INTEGER,
            learned_level INTEGER,
            cost REAL,
            duration REAL,
            start_time REAL,
            tick_time REAL,
            cooldown REAL,
            cast_time REAL,
            channel_time REAL,
            radius REAL,
            min_range REAL,
            max_range REAL,
            angle_distance REAL,
            mechanic INTEGER,
            mechanic_time REAL,
            buff_type INTEGER,
            is_toggle INTEGER NOT NULL DEFAULT 0,
            num_coef_vars INTEGER,
            coef_description TEXT,
            raw_description TEXT,
            raw_name TEXT,
            raw_tooltip TEXT,
            raw_coef TEXT,
            coef_types TEXT,
            is_mastery INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT
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
            base_mechanic INTEGER
        );
        """
    )
    db.execute("INSERT INTO skill VALUES (1, 100, 'Test Courage', 'test_courage', '', '', 5, 1, 0, 0, 0, 1, 0, NULL)")
    db.execute("INSERT INTO skill_rank (id, skill_id, ability_id, rank, morph, raw_name) VALUES (10, 1, 100, 1, 0, 'Test Courage')")
    db.execute("INSERT INTO ability VALUES (100, 0)")
    db.execute("INSERT INTO skill_coefficient VALUES (1, 10, 1, '8', 0.175015, 1.83764, -1.73373, 1.0, 5158.7)")
    db.commit()
    db.close()


def test_saved_build_resolves_skill_and_coefficient(tmp_path):
    path = tmp_path / 'eso.db'
    make_db(path)
    service = BuildMathService(path)
    snapshot = service.resolve_build(PlayerBuild(Name='Healer', BuildName='Test', FrontBarSkills=['Test Courage']))
    assert snapshot.skills[0].ability_id == 100
    assert snapshot.skills[0].skill_rank_id == 10
    result = service.evaluate_skill(snapshot, 'Test Courage', max_stat=30000, power=6000)
    assert len(result) == 1
    assert result[0].raw_value == pytest.approx(0.175015 * 30000 + 1.83764 * 6000 - 1.73373)


def test_unresolved_saved_skill_is_reported(tmp_path):
    path = tmp_path / 'eso.db'
    make_db(path)
    service = BuildMathService(path)
    snapshot = service.resolve_build(PlayerBuild(Name='Healer', FrontBarSkills=['Not In Database']))
    assert snapshot.skills == ()
    assert snapshot.unresolved_skills == ('Not In Database',)
