import sqlite3

from tools.audit_phase6_component_effect_relationships import (
    load_component_effect_relationships,
    summarize,
)


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
            type1 INTEGER, a1 REAL, b1 REAL, c1 REAL, r1 REAL, avg1 REAL,
            type2 INTEGER, a2 REAL, b2 REAL, c2 REAL, r2 REAL, avg2 REAL,
            type3 INTEGER, a3 REAL, b3 REAL, c3 REAL, r3 REAL, avg3 REAL,
            type4 INTEGER, a4 REAL, b4 REAL, c4 REAL, r4 REAL, avg4 REAL,
            type5 INTEGER, a5 REAL, b5 REAL, c5 REAL, r5 REAL, avg5 REAL,
            type6 INTEGER, a6 REAL, b6 REAL, c6 REAL, r6 REAL, avg6 REAL
        );
        CREATE TABLE combat_effect (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        INSERT INTO skill_rank VALUES
            (10, 100, 'Burning Strike', NULL, NULL, NULL, NULL),
            (20, 200, 'Plain Strike', NULL, NULL, NULL, NULL);
        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1
        ) VALUES
            (100, 'Burning Strike', 'Deal $1 Flame Damage and apply Burning.', 8, .1, 1, 0, 1, 1000),
            (200, 'Plain Strike', 'Deal $1 Flame Damage to an enemy affected by Burning.', 8, .1, 1, 0, 1, 1000);
        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000),
            (20, 1, '8', .1, 1, 0, 1, 1000);
        INSERT INTO combat_effect VALUES
            (1, 'Burning'),
            (2, 'Chilled');
        """
    )
    db.commit()
    db.close()


def test_audit_reports_only_explicit_named_effect_applications(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_component_effect_relationships(path)

    assert len(rows) == 1
    assert rows[0].skill_rank_id == 10
    assert rows[0].coefficient_number == 1
    assert rows[0].source_effect_name == "Burning"
    assert rows[0].target_effect == "burning"


def test_audit_summary_counts_relationships_components_and_abilities(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    summary = summarize(load_component_effect_relationships(path))

    assert summary["relationships"] == 1
    assert summary["components"] == 1
    assert summary["abilities"] == 1
    assert summary["effect_counts"]["Burning"] == 1
