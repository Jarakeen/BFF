import sqlite3

from minmax.skill_component_repository import SkillComponentRepository


def _make_db(path):
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

        INSERT INTO skill_component_classification VALUES
            (10, 1, 'damage', 'flame', 0, 0, NULL, 'semantic-source', 1.0),
            (10, 2, 'damage', 'flame', 0, 0, 0, 'manual-no-crit', 1.0),
            (10, 3, 'damage', 'flame', 0, 0, 1, 'manual-can-crit', 1.0),
            (10, 4, 'damage', 'flame', 0, 0, NULL, 'semantic-source', 1.0);

        CREATE TABLE skill_component_critical_evidence (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            event_family TEXT NOT NULL,
            can_crit INTEGER NOT NULL,
            source TEXT NOT NULL,
            observed_count INTEGER NOT NULL,
            evidence_json TEXT,
            PRIMARY KEY (
                skill_rank_id,
                coefficient_number,
                event_family,
                source
            )
        );

        INSERT INTO skill_component_critical_evidence VALUES
            (10, 1, 100, 'damage_direct', 1, 'runtime-log-a', 3, '{}'),
            (10, 2, 101, 'damage_direct', 1, 'runtime-log-b', 4, '{}'),
            (10, 3, 102, 'damage_direct', 1, 'runtime-log-c', 2, '{}');
        """
    )
    db.commit()
    db.close()


def test_repository_merges_positive_runtime_evidence_without_replacing_semantic_source(tmp_path):
    path = tmp_path / 'eso.db'
    _make_db(path)

    components = SkillComponentRepository(path).get_for_skill_rank(10)

    assert [component.can_crit for component in components] == [True, False, True, None]
    assert components[0].source == 'semantic-source'
    assert components[1].source == 'manual-no-crit'
    assert components[2].source == 'manual-can-crit'
    assert components[3].source == 'semantic-source'


def test_repository_without_runtime_table_preserves_null_can_crit(tmp_path):
    path = tmp_path / 'eso.db'
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
        INSERT INTO skill_component_classification VALUES
            (20, 1, 'damage', 'shock', 1, 1, NULL, 'semantic-source', 1.0);
        """
    )
    db.commit()
    db.close()

    component = SkillComponentRepository(path).get_component(20, 1)

    assert component is not None
    assert component.can_crit is None
    assert component.source == 'semantic-source'
