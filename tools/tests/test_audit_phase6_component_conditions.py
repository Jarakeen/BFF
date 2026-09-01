import sqlite3

from tools.audit_phase6_component_conditions import load_component_conditions


def test_audit_loads_explicit_health_threshold_condition(tmp_path):
    path = tmp_path / "eso.db"
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
            (10, 100, 'Execute Fixture', NULL, NULL, NULL, NULL);
        INSERT INTO ability (
            ability_id, name, coef_description, raw_description,
            type1, a1, b1, c1, r1, avg1
        ) VALUES (
            100,
            'Execute Fixture',
            'Deal $1 Magic Damage to an enemy below 25% Health.',
            'Deal damage to a low Health enemy.',
            8, .1, 1, 0, 1, 1000
        );
        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000);
        """
    )
    db.commit()
    db.close()

    rows = load_component_conditions(path)

    assert len(rows) == 1
    assert rows[0][0:4] == (10, 1, 100, 'Execute Fixture')
    assert rows[0][4] == 'target_health_below_percent'
    assert rows[0][5] == 0.25
