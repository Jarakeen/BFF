import sqlite3

from minmax.skill_critical_observation import CriticalEventFamily
from tools.audit_skill_critical_mapping import load_critical_mapping_groups


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            raw_name TEXT,
            raw_description TEXT,
            raw_tooltip TEXT,
            raw_coef TEXT,
            coef_types TEXT
        );
        CREATE TABLE skill_coefficient (
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
            name TEXT,
            coef_description TEXT,
            raw_description TEXT,
            raw_tooltip TEXT,
            type1 INTEGER, a1 REAL, b1 REAL, c1 REAL, r1 REAL, avg1 REAL,
            type2 INTEGER, a2 REAL, b2 REAL, c2 REAL, r2 REAL, avg2 REAL,
            type3 INTEGER, a3 REAL, b3 REAL, c3 REAL, r3 REAL, avg3 REAL,
            type4 INTEGER, a4 REAL, b4 REAL, c4 REAL, r4 REAL, avg4 REAL,
            type5 INTEGER, a5 REAL, b5 REAL, c5 REAL, r5 REAL, avg5 REAL,
            type6 INTEGER, a6 REAL, b6 REAL, c6 REAL, r6 REAL, avg6 REAL
        );

        INSERT INTO skill_rank VALUES
            (10, 100, 'Mixed', NULL, NULL, NULL, NULL),
            (20, 200, 'Ambiguous', NULL, NULL, NULL, NULL),
            (30, 300, 'Utility', NULL, NULL, NULL, NULL);

        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1,
            type2, a2, b2, c2, r2, avg2
        ) VALUES
            (100, 'Mixed',
             'Deal $1 Flame Damage to an enemy. The enemy takes $2 Flame Damage every 1 second for 5 seconds.',
             8, .1, 1, 0, 1, 1000,
             8, .05, .5, 0, 1, 500),
            (200, 'Ambiguous',
             'Deal $1 Physical Damage to an enemy and $2 Physical Damage to the enemy.',
             8, .1, 1, 0, 1, 1000,
             8, .08, .8, 0, 1, 800),
            (300, 'Utility',
             'Current duration: $1 seconds.',
             8, .1, 1, 0, 1, 1000,
             NULL, NULL, NULL, NULL, NULL, NULL);

        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000),
            (10, 2, '8', .05, .5, 0, 1, 500),
            (20, 1, '8', .1, 1, 0, 1, 1000),
            (20, 2, '8', .08, .8, 0, 1, 800),
            (30, 1, '8', .1, 1, 0, 1, 1000);
        """
    )
    db.commit()
    db.close()


def test_mapping_audit_separates_unique_and_ambiguous_event_families(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    groups, summary = load_critical_mapping_groups(path)

    assert summary.active_coefficients == 5
    assert summary.crit_relevant_components == 4
    assert summary.groups == 3
    assert summary.unique_groups == 2
    assert summary.ambiguous_groups == 1
    assert summary.unique_components == 2
    assert summary.ambiguous_components == 2

    mixed_direct = next(
        group
        for group in groups
        if group.ability_id == 100 and group.event_family is CriticalEventFamily.DAMAGE_DIRECT
    )
    mixed_dot = next(
        group
        for group in groups
        if group.ability_id == 100 and group.event_family is CriticalEventFamily.DAMAGE_PERIODIC
    )
    ambiguous = next(group for group in groups if group.ability_id == 200)

    assert mixed_direct.is_unique
    assert mixed_direct.candidates[0].coefficient_number == 1
    assert mixed_dot.is_unique
    assert mixed_dot.candidates[0].coefficient_number == 2
    assert not ambiguous.is_unique
    assert {candidate.coefficient_number for candidate in ambiguous.candidates} == {1, 2}


def test_mapping_audit_excludes_utility_components(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    groups, _ = load_critical_mapping_groups(path)

    assert all(group.ability_id != 300 for group in groups)
