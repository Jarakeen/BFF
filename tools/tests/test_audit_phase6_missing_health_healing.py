import sqlite3

from tools.audit_phase6_missing_health_healing import load_missing_health_healing_audit


def test_audit_promotes_missing_health_healing_candidate(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            skill_id INTEGER,
            rank INTEGER,
            morph INTEGER
        );
        CREATE TABLE skill_coefficient (
            id INTEGER PRIMARY KEY,
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            type INTEGER,
            a REAL,
            b REAL,
            c REAL,
            r REAL,
            avg REAL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            coef_description TEXT
        );
        CREATE TABLE skill_component_classification (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            effect_kind TEXT,
            damage_type TEXT,
            is_dot INTEGER,
            is_aoe INTEGER,
            can_crit INTEGER,
            source TEXT,
            confidence REAL
        );
        INSERT INTO skill_rank VALUES (10, 100, 1, 1, 0);
        INSERT INTO skill_coefficient VALUES (1, 10, 1, 1, 1, 1, 1, 1, 1);
        INSERT INTO ability VALUES (
            100,
            'Drain Example',
            'Siphon away your enemies vitality, dealing $1 Magic Damage and healing you for 25% of your missing Health every 1 second for 3 seconds.'
        );
        INSERT INTO skill_component_classification VALUES (
            10, 1, 'damage', 'magical', 1, 0, NULL, 'test', 1.0
        );
        """
    )
    db.commit()
    db.close()

    rows = load_missing_health_healing_audit(path)

    assert len(rows) == 1
    assert rows[0].status == "PROMOTED"
    assert rows[0].fraction == 0.25
