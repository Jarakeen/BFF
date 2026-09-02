import sqlite3

from minmax.skill_component_role import SkillComponentRoleType
from minmax.skill_component_role_repository import SkillComponentRoleRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);

        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'When triggered, the trap deals $1 Bleed Damage, an additional $2 Bleed Damage over 20 seconds.'
        );

        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'Infuse your weapon, causing your next Light Attack to deal an additional $1 Physical Damage.'
        );

        INSERT INTO skill_rank VALUES (30, 300);
        INSERT INTO ability VALUES (
            300,
            'The wards protect allies for $1 damage. The wards also heal you and your group members for $2 Health over 15 seconds.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_same_ability_additional_damage(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    roles = SkillComponentRoleRepository(path).resolve(10, 2)
    assert len(roles) == 1
    assert roles[0].role_type is SkillComponentRoleType.ADDITIONAL_DAMAGE


def test_repository_does_not_promote_triggered_single_coefficient_damage(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    assert SkillComponentRoleRepository(path).resolve(20, 1) == ()


def test_repository_resolves_additional_heal(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    roles = SkillComponentRoleRepository(path).resolve(30, 2)
    assert len(roles) == 1
    assert roles[0].role_type is SkillComponentRoleType.ADDITIONAL_HEAL


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    assert SkillComponentRoleRepository(path).resolve(999, 1) == ()
