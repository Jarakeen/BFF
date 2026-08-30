import sqlite3

from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository


def test_missing_component_table_returns_no_guesses(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    repo = SkillComponentRepository(path)

    assert repo.get_for_skill_rank(123) == ()
    assert repo.get_component(123, 1) is None


def test_repository_reads_explicit_per_coefficient_identity(tmp_path):
    path = tmp_path / "eso.db"
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
            (123, 1, 'damage', 'Flame', 0, 0, 1, 'verified fixture', 1.0),
            (123, 2, 'heal', NULL, NULL, 1, 1, 'verified fixture', 1.0);
        """
    )
    db.commit()
    db.close()

    repo = SkillComponentRepository(path)
    components = repo.get_for_skill_rank(123)

    assert len(components) == 2
    assert components[0].effect_kind is SkillEffectKind.DAMAGE
    assert components[0].damage_type == "flame"
    assert components[0].is_dot is False
    assert components[0].is_aoe is False
    assert components[0].can_crit is True
    assert components[0].is_complete_damage_identity
    assert components[1].effect_kind is SkillEffectKind.HEAL
    assert not components[1].is_complete_damage_identity


def test_unknown_effect_kind_stays_unknown(tmp_path):
    path = tmp_path / "eso.db"
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
            confidence REAL
        );
        INSERT INTO skill_component_classification VALUES
            (321, 1, 'mystery', NULL, NULL, NULL, NULL, 'unresolved fixture', NULL);
        """
    )
    db.commit()
    db.close()

    component = SkillComponentRepository(path).get_component(321, 1)

    assert component is not None
    assert component.effect_kind is SkillEffectKind.UNKNOWN
    assert component.damage_type is None
    assert component.is_dot is None
    assert component.is_aoe is None
    assert component.can_crit is None
