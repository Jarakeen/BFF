import json
import sqlite3

from importers.skill_critical_observation_importer import (
    EVIDENCE_TABLE,
    import_runtime_critical_evidence,
    load_runtime_critical_observations,
)
from minmax.skill_critical_observation import CriticalEventFamily, RuntimeCriticalObservation


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
            (10, 100, 'Unique Direct', NULL, NULL, NULL, NULL),
            (20, 200, 'Ambiguous Direct', NULL, NULL, NULL, NULL),
            (30, 300, 'Unique Dot', NULL, NULL, NULL, NULL);

        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1,
            type2, a2, b2, c2, r2, avg2
        ) VALUES
            (100, 'Unique Direct', 'Deal $1 Flame Damage to an enemy.',
             8, .1, 1, 0, 1, 1000,
             NULL, NULL, NULL, NULL, NULL, NULL),
            (200, 'Ambiguous Direct', 'Deal $1 Flame Damage and $2 Flame Damage to an enemy.',
             8, .1, 1, 0, 1, 1000,
             8, .05, .5, 0, 1, 500),
            (300, 'Unique Dot', 'Deal $1 Poison Damage every 1 second for 5 seconds to an enemy.',
             8, .05, .5, 0, 1, 500,
             NULL, NULL, NULL, NULL, NULL, NULL);

        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000),
            (20, 1, '8', .1, 1, 0, 1, 1000),
            (20, 2, '8', .05, .5, 0, 1, 500),
            (30, 1, '8', .05, .5, 0, 1, 500);
        """
    )
    db.commit()
    db.close()


def _obs(ability_id, family, source='fixture-log', count=1):
    return RuntimeCriticalObservation(
        ability_id=ability_id,
        event_family=family,
        source=source,
        observed_count=count,
    )


def test_json_and_jsonl_observation_loader(tmp_path):
    array_path = tmp_path / 'obs.json'
    array_path.write_text(
        json.dumps([
            {
                'ability_id': 100,
                'event_family': 'damage_direct',
                'source': 'report-a',
                'observed_count': 3,
            }
        ]),
        encoding='utf-8',
    )
    loaded = load_runtime_critical_observations(array_path)
    assert loaded == (
        _obs(100, CriticalEventFamily.DAMAGE_DIRECT, 'report-a', 3),
    )

    jsonl_path = tmp_path / 'obs.jsonl'
    jsonl_path.write_text(
        '{"ability_id":100,"event_family":"damage_direct","source":"a"}\n'
        '{"ability_id":300,"event_family":"damage_periodic","source":"b","observed_count":2}\n',
        encoding='utf-8',
    )
    loaded = load_runtime_critical_observations(jsonl_path)
    assert len(loaded) == 2
    assert loaded[1].observed_count == 2


def test_dry_run_resolves_unique_without_creating_evidence_table(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    summary = import_runtime_critical_evidence(
        path,
        (_obs(100, CriticalEventFamily.DAMAGE_DIRECT, count=4),),
    )

    assert summary.resolved_components == 1
    assert summary.write_eligible_rows == 1
    assert summary.rows_written == 0

    db = sqlite3.connect(path)
    table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (EVIDENCE_TABLE,),
    ).fetchone()
    db.close()
    assert table is None


def test_write_persists_only_unique_positive_observation(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    summary = import_runtime_critical_evidence(
        path,
        (
            _obs(100, CriticalEventFamily.DAMAGE_DIRECT, 'report-a', 4),
            _obs(200, CriticalEventFamily.DAMAGE_DIRECT, 'report-b', 7),
            _obs(999, CriticalEventFamily.DAMAGE_DIRECT, 'report-c', 2),
        ),
        dry_run=False,
    )

    assert summary.resolved_components == 1
    assert summary.ambiguous_observations == 1
    assert summary.unmatched_observations == 1
    assert summary.rows_written == 1

    db = sqlite3.connect(path)
    rows = db.execute(
        f"""
        SELECT skill_rank_id, coefficient_number, ability_id, event_family,
               can_crit, source, observed_count
        FROM {EVIDENCE_TABLE}
        """
    ).fetchall()
    db.close()
    assert rows == [(10, 1, 100, 'damage_direct', 1, 'report-a', 4)]


def test_same_source_reimport_replaces_count_instead_of_double_counting(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    import_runtime_critical_evidence(
        path,
        (_obs(100, CriticalEventFamily.DAMAGE_DIRECT, 'same-report', 2),),
        dry_run=False,
    )
    import_runtime_critical_evidence(
        path,
        (_obs(100, CriticalEventFamily.DAMAGE_DIRECT, 'same-report', 5),),
        dry_run=False,
    )

    db = sqlite3.connect(path)
    rows = db.execute(
        f"SELECT source, observed_count FROM {EVIDENCE_TABLE}"
    ).fetchall()
    db.close()
    assert rows == [('same-report', 5)]


def test_explicit_classification_can_crit_is_never_overwritten(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_component_classification (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            effect_kind TEXT NOT NULL,
            damage_type TEXT,
            is_dot INTEGER,
            is_aoe INTEGER,
            can_crit INTEGER,
            source TEXT,
            confidence REAL,
            PRIMARY KEY (skill_rank_id, coefficient_number)
        );
        INSERT INTO skill_component_classification (
            skill_rank_id, coefficient_number, effect_kind, damage_type,
            is_dot, is_aoe, can_crit, source, confidence
        ) VALUES (10, 1, 'damage', 'flame', 0, 0, 0, 'manual no-crit proof', 1.0);
        """
    )
    db.commit()
    db.close()

    summary = import_runtime_critical_evidence(
        path,
        (_obs(100, CriticalEventFamily.DAMAGE_DIRECT),),
        dry_run=False,
    )

    assert summary.already_classified_observations == 1
    assert summary.resolved_components == 0
    assert summary.rows_written == 0

    db = sqlite3.connect(path)
    rows = db.execute(f"SELECT * FROM {EVIDENCE_TABLE}").fetchall()
    explicit = db.execute(
        "SELECT can_crit, source FROM skill_component_classification WHERE skill_rank_id=10"
    ).fetchone()
    db.close()
    assert rows == []
    assert explicit == (0, 'manual no-crit proof')


def test_empty_observation_set_never_creates_false_evidence(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    summary = import_runtime_critical_evidence(path, (), dry_run=False)
    assert summary.resolved_components == 0
    assert summary.rows_written == 0

    db = sqlite3.connect(path)
    false_rows = db.execute(
        f"SELECT COUNT(*) FROM {EVIDENCE_TABLE} WHERE can_crit = 0"
    ).fetchone()[0]
    db.close()
    assert false_rows == 0
