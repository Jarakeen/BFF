import sqlite3

from tools.audit_skill_component_import_gaps import (
    load_import_gaps,
    sample_gap_rows,
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
            (10, 100, 'Complete', NULL, NULL, NULL, NULL),
            (20, 200, 'Unknown Kind', NULL, NULL, NULL, NULL),
            (30, 300, 'Unknown Shape', NULL, NULL, NULL, NULL),
            (40, 400, 'No Fragment', NULL, NULL, NULL, NULL),
            (50, 500, 'Mismatch', NULL, NULL, NULL, NULL),
            (60, 600, 'Known Shield', NULL, NULL, NULL, NULL),
            (70, 700, 'Known Utility', NULL, NULL, NULL, NULL);

        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1
        ) VALUES
            (100, 'Complete', 'Deal $1 Flame Damage to an enemy.', 8, .1, 1, 0, 1, 1000),
            (200, 'Unknown Kind', 'Increase a mysterious value by $1.', 8, .1, 1, 0, 1, 1000),
            (300, 'Unknown Shape', 'Inflict $1 Flame Damage.', 8, .1, 1, 0, 1, 1000),
            (400, 'No Fragment', 'No coefficient placeholder here.', 8, .1, 1, 0, 1, 1000),
            (500, 'Mismatch', 'Deal $1 Physical Damage to an enemy.', 8, .2, 1, 0, 1, 1000),
            (600, 'Known Shield', 'Gain a damage shield that absorbs $1 damage for 6 seconds.', 8, .1, 1, 0, 1, 1000),
            (700, 'Known Utility', 'Current duration: $1 seconds.', 8, .1, 1, 0, 1, 1000);

        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000),
            (20, 1, '8', .1, 1, 0, 1, 1000),
            (30, 1, '8', .1, 1, 0, 1, 1000),
            (40, 1, '8', .1, 1, 0, 1, 1000),
            (50, 1, '8', .1, 1, 0, 1, 1000),
            (60, 1, '8', .1, 1, 0, 1, 1000),
            (70, 1, '8', .1, 1, 0, 1, 1000);
        """
    )
    db.commit()
    db.close()


def test_gap_audit_reports_only_unresolved_active_components(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    gaps = load_import_gaps(path)

    assert len(gaps) == 4
    assert {row.name for row in gaps} == {
        "Unknown Kind",
        "Unknown Shape",
        "No Fragment",
        "Mismatch",
    }


def test_gap_audit_counts_only_fields_required_for_effect_family(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    gaps = load_import_gaps(path)
    summary = summarize(gaps)

    unknown_shape = next(row for row in gaps if row.name == "Unknown Shape")
    assert unknown_shape.reasons == ("target_shape",)

    field_counts = summary["field_counts"]
    combination_counts = summary["combination_counts"]

    assert summary["rows"] == 4
    assert field_counts["effect_kind"] == 1
    assert field_counts["periodicity"] == 0
    assert field_counts["target_shape"] == 1
    assert field_counts["missing_fragment"] == 1
    assert field_counts["slot_mismatch"] == 1
    assert combination_counts[("target_shape",)] == 1


def test_complete_component_shield_and_utility_are_not_reported_as_gaps(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    gaps = load_import_gaps(path)

    names = {row.name for row in gaps}
    assert "Complete" not in names
    assert "Known Shield" not in names
    assert "Known Utility" not in names


def test_gap_samples_round_robin_across_reason_combinations(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    gaps = load_import_gaps(path)
    samples = sample_gap_rows(gaps, 4)

    assert len(samples) == 4
    assert {row.reasons for row in samples} == {
        ("effect_kind",),
        ("target_shape",),
        ("missing_fragment",),
        ("slot_mismatch",),
    }


def test_gap_samples_zero_limit_returns_empty(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert sample_gap_rows(load_import_gaps(path), 0) == ()
