import sqlite3

from tools.audit_phase6_condition_ownership import load_condition_ownership


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            coef1 REAL,
            coef2 REAL,
            coef3 REAL,
            coef_type1 INTEGER,
            coef_type2 INTEGER,
            coef_type3 INTEGER
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            coef_description TEXT
        );
        INSERT INTO skill_rank VALUES (10, 100, 1.0, 1.0, 1.0, 0, 0, 0);
        INSERT INTO ability VALUES (
            100,
            'Fixture Skill',
            'Deal $1 Magic Damage. The second hit deals $2 Magic Damage and heals you for $3 Health while the enemy is below 25% Health.'
        );
        """
    )
    db.commit()
    db.close()


def test_condition_ownership_audit_keeps_all_active_components_for_conditioned_ability(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_condition_ownership(path)

    assert [row.coefficient_number for row in rows] == [1, 2, 3]
    assert any(row.owns_condition for row in rows)
    assert {row.effect_kind for row in rows} >= {"damage", "heal"}


def test_condition_ownership_audit_marks_current_owner_without_reassigning(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_condition_ownership(path)
    owners = [row for row in rows if row.owns_condition]

    assert len(owners) == 1
    assert owners[0].coefficient_number == 3
    assert owners[0].thresholds == (0.25,)
