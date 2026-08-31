import json
import sqlite3

from importers.skill_component_classification_importer import (
    SOURCE,
    import_skill_component_classifications,
)
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository


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
            (10, 100, 'Meteor Fixture', NULL, NULL, NULL, NULL),
            (20, 200, 'Incomplete Fixture', NULL, NULL, NULL, NULL),
            (30, 300, 'Mismatch Fixture', NULL, NULL, NULL, NULL);

        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1,
            type2, a2, b2, c2, r2, avg2
        ) VALUES
            (100, 'Meteor Fixture',
             'Deal |cffffff$1|r Flame Damage to all enemies in the area. After impact, all enemies hit take |cffffff$2|r Flame Damage every |cffffff1|r second for |cffffff5|r seconds.',
             8, .1, 1.0, 0, 1, 1000,
             8, .05, .5, 0, 1, 500),
            (200, 'Incomplete Fixture',
             'Deal |cffffff$1|r Damage to an enemy.',
             8, .1, 1.0, 0, 1, 1000,
             NULL, NULL, NULL, NULL, NULL, NULL),
            (300, 'Mismatch Fixture',
             'Deal |cffffff$1|r Physical Damage to an enemy.',
             8, .2, 1.0, 0, 1, 1000,
             NULL, NULL, NULL, NULL, NULL, NULL);

        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1.0, 0, 1, 1000),
            (10, 2, '8', .05, .5, 0, 1, 500),
            (10, 3, '-1', -1, -1, -1, -1, -1),
            (20, 1, '8', .1, 1.0, 0, 1, 1000),
            (30, 1, '8', .1, 1.0, 0, 1, 1000);
        """
    )
    db.commit()
    db.close()


def _create_classification_table(db):
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
            evidence_fragment TEXT,
            evidence_json TEXT,
            PRIMARY KEY (skill_rank_id, coefficient_number)
        );
        """
    )


def test_importer_writes_only_complete_verified_active_components(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    summary = import_skill_component_classifications(path, dry_run=False)

    assert summary.scanned == 5
    assert summary.active == 4
    assert summary.qualified == 2
    assert summary.write_eligible == 2
    assert summary.inserted == 2
    assert summary.removed_derived == 0
    assert summary.protected_existing == 0
    assert summary.skipped_inactive == 1
    assert summary.skipped_slot_mismatch == 1
    assert summary.skipped_incomplete == 1

    db = sqlite3.connect(path)
    rows = db.execute(
        """
        SELECT skill_rank_id, coefficient_number, effect_kind, damage_type,
               is_dot, is_aoe, can_crit, source, confidence,
               evidence_fragment, evidence_json
        FROM skill_component_classification
        ORDER BY skill_rank_id, coefficient_number
        """
    ).fetchall()
    db.close()

    assert len(rows) == 2
    assert rows[0][0:7] == (10, 1, 'damage', 'flame', 0, 1, None)
    assert rows[1][0:7] == (10, 2, 'damage', 'flame', 1, 1, None)
    assert rows[0][7] == SOURCE
    assert 'upstream provenance unresolved' in rows[0][7]
    assert rows[0][8] == 1.0
    assert '$1 Flame Damage' in rows[0][9]
    assert 'placeholder explicitly precedes Flame Damage' in json.loads(rows[0][10])


def test_imported_rows_are_readable_by_runtime_repository(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    import_skill_component_classifications(path, dry_run=False)

    components = SkillComponentRepository(path).get_for_skill_rank(10)

    assert len(components) == 2
    assert components[0].effect_kind is SkillEffectKind.DAMAGE
    assert components[0].damage_type == 'flame'
    assert components[0].is_dot is False
    assert components[0].is_aoe is True
    assert components[0].can_crit is None
    assert not components[0].is_complete_damage_identity
    assert components[1].is_dot is True


def test_importer_persists_explicit_shield_without_fake_damage_routing_fields(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO skill_rank VALUES (40, 400, 'Shield Fixture', NULL, NULL, NULL, NULL)"
    )
    db.execute(
        """
        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            400,
            'Shield Fixture',
            'You gain a damage shield that absorbs $1 damage for 6 seconds.',
            8, .1, 1.0, 0, 1, 1000,
        ),
    )
    db.execute("INSERT INTO skill_coefficient VALUES (40, 1, '8', .1, 1.0, 0, 1, 1000)")
    db.commit()
    db.close()

    summary = import_skill_component_classifications(path, dry_run=False)
    component = SkillComponentRepository(path).get_component(40, 1)

    assert summary.qualified == 3
    assert component is not None
    assert component.effect_kind is SkillEffectKind.SHIELD
    assert component.damage_type is None
    assert component.is_dot is None
    assert component.is_aoe is None
    assert component.can_crit is None
    assert not component.is_complete_damage_identity


def test_importer_persists_explicit_utility_without_fake_damage_routing_fields(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO skill_rank VALUES (40, 400, 'Utility Fixture', NULL, NULL, NULL, NULL)"
    )
    db.execute(
        """
        INSERT INTO ability (
            ability_id, name, coef_description,
            type1, a1, b1, c1, r1, avg1
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (400, 'Utility Fixture', 'Current duration: $1 seconds.', 8, .1, 1.0, 0, 1, 1000),
    )
    db.execute("INSERT INTO skill_coefficient VALUES (40, 1, '8', .1, 1.0, 0, 1, 1000)")
    db.commit()
    db.close()

    summary = import_skill_component_classifications(path, dry_run=False)
    component = SkillComponentRepository(path).get_component(40, 1)

    assert summary.qualified == 3
    assert component is not None
    assert component.effect_kind is SkillEffectKind.UTILITY
    assert component.damage_type is None
    assert component.is_dot is None
    assert component.is_aoe is None
    assert component.can_crit is None
    assert not component.is_complete_damage_identity


def test_importer_upgrades_existing_legacy_table_with_evidence_columns(tmp_path):
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
        """
    )
    db.commit()
    db.close()

    import_skill_component_classifications(path, dry_run=False)

    db = sqlite3.connect(path)
    columns = {row[1] for row in db.execute('PRAGMA table_info(skill_component_classification)')}
    db.close()

    assert 'evidence_fragment' in columns
    assert 'evidence_json' in columns


def test_api_defaults_to_read_only_dry_run(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    db = sqlite3.connect(path)
    before_schema = tuple(db.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall())
    db.close()

    summary = import_skill_component_classifications(path)

    assert summary.scanned == 5
    assert summary.active == 4
    assert summary.qualified == 2
    assert summary.write_eligible == 2
    assert summary.inserted == 0

    db = sqlite3.connect(path)
    after_schema = tuple(db.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall())
    table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_component_classification'"
    ).fetchone()
    db.close()

    assert before_schema == after_schema
    assert table is None


def test_foreign_manual_row_is_never_overwritten(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    db = sqlite3.connect(path)
    _create_classification_table(db)
    db.execute(
        """
        INSERT INTO skill_component_classification (
            skill_rank_id, coefficient_number, effect_kind, damage_type,
            is_dot, is_aoe, can_crit, source, confidence,
            evidence_fragment, evidence_json
        ) VALUES (10, 1, 'damage', 'shock', 0, 0, 1, 'manual verification', 1.0, 'manual', '[]')
        """
    )
    db.commit()
    db.close()

    preflight = import_skill_component_classifications(path)
    result = import_skill_component_classifications(path, dry_run=False)

    assert preflight.qualified == 2
    assert preflight.write_eligible == 1
    assert preflight.protected_existing == 1
    assert result.inserted == 1
    assert result.protected_existing == 1

    db = sqlite3.connect(path)
    protected = db.execute(
        """
        SELECT damage_type, is_aoe, can_crit, source, evidence_fragment
        FROM skill_component_classification
        WHERE skill_rank_id = 10 AND coefficient_number = 1
        """
    ).fetchone()
    db.close()

    assert protected == ('shock', 0, 1, 'manual verification', 'manual')


def test_rebuild_deletes_only_rows_owned_by_this_extractor(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)
    db = sqlite3.connect(path)
    _create_classification_table(db)
    db.execute(
        """
        INSERT INTO skill_component_classification (
            skill_rank_id, coefficient_number, effect_kind, source
        ) VALUES (?, ?, ?, ?)
        """,
        (999, 1, 'shield', SOURCE),
    )
    db.execute(
        """
        INSERT INTO skill_component_classification (
            skill_rank_id, coefficient_number, effect_kind, source
        ) VALUES (?, ?, ?, ?)
        """,
        (998, 1, 'shield', 'manual verification'),
    )
    db.commit()
    db.close()

    preflight = import_skill_component_classifications(path)
    assert preflight.removed_derived == 1

    result = import_skill_component_classifications(path, dry_run=False)
    assert result.removed_derived == 1

    db = sqlite3.connect(path)
    manual = db.execute(
        "SELECT effect_kind, source FROM skill_component_classification WHERE skill_rank_id = 998"
    ).fetchone()
    old_derived = db.execute(
        "SELECT 1 FROM skill_component_classification WHERE skill_rank_id = 999"
    ).fetchone()
    db.close()

    assert manual == ('shield', 'manual verification')
    assert old_derived is None
