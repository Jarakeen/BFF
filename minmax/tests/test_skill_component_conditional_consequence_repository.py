import sqlite3

from minmax.skill_component_conditional_consequence import SkillComponentConditionalConsequenceType
from minmax.skill_component_conditional_consequence_repository import (
    SkillComponentConditionalConsequenceRepository,
)


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);

        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Deal $1 Shock Damage. If the enemy falls to or below 20% Health, an explosion deals an additional $2 Shock Damage.'
        );

        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'Deal $1 Physical Damage and $2 Bleed Damage. The second hit deals up to 125% more damage to enemies with lessthan 25% Health and heals you for $3 Health.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_condition_gated_secondary_damage(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    consequences = SkillComponentConditionalConsequenceRepository(path).resolve(10, 2)

    assert len(consequences) == 1
    assert consequences[0].consequence_type is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT
    assert consequences[0].maximum_bonus_fraction is None


def test_repository_uses_ordinal_sentence_for_damage_amplification(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    repository = SkillComponentConditionalConsequenceRepository(path)
    second = repository.resolve(20, 2)
    third = repository.resolve(20, 3)

    assert len(second) == 1
    assert second[0].consequence_type is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE
    assert second[0].maximum_bonus_fraction == 1.25
    assert third == ()


def test_repository_returns_empty_for_unconditioned_component(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentConditionalConsequenceRepository(path).resolve(10, 1) == ()


def test_repository_fails_closed_for_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    assert SkillComponentConditionalConsequenceRepository(path).resolve(10, 1) == ()
