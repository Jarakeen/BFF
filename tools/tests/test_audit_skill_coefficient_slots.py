import sqlite3

from tools.audit_skill_coefficient_slots import load_slot_audit, summarize


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
            type1 INTEGER,
            a1 REAL,
            b1 REAL,
            c1 REAL,
            r1 REAL,
            avg1 REAL,
            type2 INTEGER,
            a2 REAL,
            b2 REAL,
            c2 REAL,
            r2 REAL,
            avg2 REAL,
            type3 INTEGER,
            a3 REAL,
            b3 REAL,
            c3 REAL,
            r3 REAL,
            avg3 REAL,
            type4 INTEGER,
            a4 REAL,
            b4 REAL,
            c4 REAL,
            r4 REAL,
            avg4 REAL,
            type5 INTEGER,
            a5 REAL,
            b5 REAL,
            c5 REAL,
            r5 REAL,
            avg5 REAL,
            type6 INTEGER,
            a6 REAL,
            b6 REAL,
            c6 REAL,
            r6 REAL,
            avg6 REAL
        );

        INSERT INTO skill_rank VALUES (
            10, 100, 'Mixed Skill',
            'Deal <<1>> Flame Damage, then heal for <<2>> Health.',
            'Deal <<1>> Flame Damage, then heal for <<2>> Health.',
            'raw coefficient payload', '8,8'
        );
        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', 0.10, 1.20, 3.0, 0.99, 1000.0),
            (10, 2, '8', 0.20, 1.40, 4.0, 0.98, 2000.0);
        INSERT INTO ability VALUES (
            100, 'Mixed Skill',
            'Deal $1 Flame Damage, then heal for $2 Health.',
            'Deal <<1>> Flame Damage, then heal for <<2>> Health.',
            NULL,
            8, 0.10, 1.20, 3.0, 0.99, 1000.0,
            8, 0.20, 1.40, 4.0, 0.98, 2000.0,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL
        );

        INSERT INTO skill_rank VALUES (
            20, 200, 'Mismatch Skill', NULL, 'Value <<1>>.', NULL, NULL
        );
        INSERT INTO skill_coefficient VALUES
            (20, 1, '8', 0.50, 2.00, 5.0, 1.0, NULL);
        INSERT INTO ability VALUES (
            200, 'Mismatch Skill', 'Value $1.', NULL, NULL,
            8, 9.99, 2.00, 5.0, 1.0, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL
        );
        """
    )
    db.commit()
    db.close()


def test_slot_audit_matches_normalized_rows_to_same_numbered_raw_slots(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_slot_audit(path, skill_rank_id=10)

    assert len(rows) == 2
    assert rows[0].coefficient_number == 1
    assert rows[0].raw_slot_matches_coefficient is True
    assert rows[1].coefficient_number == 2
    assert rows[1].raw_slot_matches_coefficient is True


def test_slot_audit_collects_dollar_and_angle_placeholders_without_assigning_semantics(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_slot_audit(path, skill_rank_id=10)

    assert rows[0].placeholder_numbers == (1, 2)
    assert rows[0].slot_placeholder_is_present is True
    assert rows[1].placeholder_numbers == (1, 2)
    assert rows[1].slot_placeholder_is_present is True


def test_slot_audit_exposes_raw_slot_mismatch_instead_of_smoothing_it_over(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    row = load_slot_audit(path, ability_id=200)[0]

    assert row.raw_slot_matches_coefficient is False
    counts = summarize((row,))
    assert counts["raw_slot_mismatch"] == 1
    assert counts["raw_slot_match"] == 0


def test_summary_counts_alignment_and_placeholder_evidence(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    rows = load_slot_audit(path)
    counts = summarize(rows)

    assert counts == {
        "components": 3,
        "raw_slot_present": 3,
        "raw_slot_match": 2,
        "raw_slot_mismatch": 1,
        "slot_placeholder_present": 3,
        "any_placeholder": 3,
    }
