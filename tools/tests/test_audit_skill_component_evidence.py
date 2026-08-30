import sqlite3

from tools.audit_skill_component_evidence import load_component_evidence, summarize


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            raw_name TEXT
        );
        CREATE TABLE skill_coefficient (
            id INTEGER PRIMARY KEY,
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            target TEXT,
            duration REAL,
            tick_time REAL,
            radius REAL,
            is_channeled INTEGER,
            coef_description TEXT,
            raw_description TEXT,
            raw_tooltip TEXT
        );
        INSERT INTO skill_rank VALUES (10, 101, 'Fallback Name');
        INSERT INTO skill_coefficient VALUES (1, 10, 1);
        INSERT INTO skill_coefficient VALUES (2, 10, 2);
        INSERT INTO ability VALUES (
            101,
            'Evidence Skill',
            'Enemy',
            8000,
            1000,
            6,
            0,
            'Coefficient evidence',
            'Deals damage over time.',
            'Tooltip evidence'
        );
        """
    )
    db.commit()
    db.close()


def test_audit_reads_same_ability_evidence_for_each_coefficient(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    rows = load_component_evidence(path)

    assert [row.coefficient_number for row in rows] == [1, 2]
    assert all(row.skill_rank_id == 10 for row in rows)
    assert all(row.ability_id == 101 for row in rows)
    assert all(row.name == 'Evidence Skill' for row in rows)
    assert all(row.target == 'Enemy' for row in rows)
    assert all(row.duration == 8000 for row in rows)
    assert all(row.tick_time == 1000 for row in rows)
    assert all(row.radius == 6 for row in rows)


def test_summary_counts_evidence_without_classifying_mechanics(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    counts = summarize(load_component_evidence(path))

    assert counts == {
        'components': 2,
        'target': 2,
        'timing': 2,
        'radius': 2,
        'channeled': 0,
        'text': 2,
    }


def test_filters_by_skill_rank_or_ability_id(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    by_rank = load_component_evidence(path, skill_rank_id=10)
    by_ability = load_component_evidence(path, ability_id=101)
    missing = load_component_evidence(path, ability_id=999)

    assert len(by_rank) == 2
    assert len(by_ability) == 2
    assert missing == ()
