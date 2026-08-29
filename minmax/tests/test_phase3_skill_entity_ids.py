from __future__ import annotations

import sqlite3

from minmax.skill_coefficient_repository import (
    SkillCoefficientRepository,
    ability_entity_id,
)


def _db(tmp_path):
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            base_ability_id INTEGER NOT NULL,
            name TEXT
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            rank INTEGER,
            morph INTEGER,
            raw_name TEXT
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

        INSERT INTO skill VALUES (1, 1000, 'Deep Fissure');
        INSERT INTO ability VALUES (1001, 'Deep Fissure');
        INSERT INTO ability VALUES (1002, 'Deep Fissure');
        INSERT INTO ability VALUES (1003, 'Deep Fissure');
        INSERT INTO ability VALUES (1004, 'Deep Fissure');
        INSERT INTO skill_rank VALUES (11, 1, 1001, 1, 1, 'Deep Fissure');
        INSERT INTO skill_rank VALUES (12, 1, 1002, 2, 1, 'Deep Fissure');
        INSERT INTO skill_rank VALUES (13, 1, 1003, 3, 1, 'Deep Fissure');
        INSERT INTO skill_rank VALUES (14, 1, 1004, 4, 1, 'Deep Fissure');
        INSERT INTO skill_coefficient VALUES
            (1, 14, 1, '8', 0.1, 1.0, 0.0, 1.0, NULL);
        """
    )
    connection.commit()
    connection.close()
    return path


def test_ability_entity_id_is_lower_snake_case_name():
    assert ability_entity_id("Deep Fissure") == "deep_fissure"
    assert ability_entity_id("Fetcher Infection") == "fetcher_infection"
    assert ability_entity_id("Nature's Grasp") == "natures_grasp"


def test_one_entity_can_have_multiple_numeric_ability_ids(tmp_path):
    repository = SkillCoefficientRepository(_db(tmp_path))

    resolution = repository.resolve_entity_id("deep_fissure")

    assert resolution.unresolved == ()
    assert resolution.rank is not None
    assert resolution.rank.entity_id == "deep_fissure"
    assert resolution.rank.name == "Deep Fissure"
    assert resolution.rank.rank == 4
    assert resolution.rank.ability_id == 1004


def test_numeric_ability_id_is_a_crosswalk_not_the_entity_identity(tmp_path):
    repository = SkillCoefficientRepository(_db(tmp_path))

    low_rank = repository.resolve_ability_id(1001)
    high_rank = repository.resolve_ability_id(1004)

    assert low_rank.rank is not None
    assert high_rank.rank is not None
    assert low_rank.rank.entity_id == "deep_fissure"
    assert high_rank.rank.entity_id == "deep_fissure"
    assert low_rank.rank.ability_id != high_rank.rank.ability_id
