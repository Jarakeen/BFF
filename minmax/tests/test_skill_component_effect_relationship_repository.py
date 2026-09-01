import sqlite3

from minmax.skill_component_effect_relationship import (
    SkillComponentEffectRelationshipType,
)
from minmax.skill_component_effect_relationship_repository import (
    SkillComponentEffectRelationshipRepository,
)


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            coef_description TEXT
        );
        CREATE TABLE combat_effect (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        INSERT INTO skill_rank VALUES (4474, 20492);
        INSERT INTO ability VALUES (
            20492,
            'The searing metal deals $1 Flame Damage, applies the Burning status effect, and taunts them for 15 seconds.'
        );
        INSERT INTO combat_effect VALUES
            (1, 'Burning'),
            (2, 'Chilled');
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_explicit_known_effect_application(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    relationships = SkillComponentEffectRelationshipRepository(path).resolve(4474, 1)

    assert len(relationships) == 1
    relationship = relationships[0]
    assert relationship.relationship_type is SkillComponentEffectRelationshipType.APPLIES
    assert relationship.target_effect == "burning"
    assert relationship.source_effect_name == "Burning"


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentEffectRelationshipRepository(path).resolve(9999, 1) == ()


def test_repository_does_not_use_whole_ability_text_for_missing_component(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentEffectRelationshipRepository(path).resolve(4474, 2) == ()


def test_repository_requires_canonical_combat_effect_vocabulary(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        CREATE TABLE combat_effect (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (100, 'Deal $1 Magic Damage and apply Imaginary Doom.');
        INSERT INTO combat_effect VALUES (1, 'Burning');
        """
    )
    db.commit()
    db.close()

    assert SkillComponentEffectRelationshipRepository(path).resolve(10, 1) == ()


def test_repository_fails_closed_when_required_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    assert SkillComponentEffectRelationshipRepository(path).resolve(10, 1) == ()
