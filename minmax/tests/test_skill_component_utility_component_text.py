import sqlite3

from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)


def test_repository_exposes_same_owned_text_used_for_taunt_resolution(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
            CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
            INSERT INTO skill_rank VALUES (15, 150);
            INSERT INTO ability VALUES (
                150,
                'Thrust your weapon at an enemy, dealing $1 Physical Damage and taunting them to attack you for 15 seconds.'
            );
            """
        )

    repo = SkillComponentUtilityEffectRepository(path)
    component_text = repo.resolve_component_text(15, 1)

    assert "$1 Physical Damage" in component_text
    assert "taunting them to attack you for 15 seconds" in component_text
    assert [item.effect_type for item in repo.resolve(15, 1)] == [
        SkillComponentUtilityEffectType.TAUNT
    ]


def test_component_text_fails_closed_when_source_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    assert SkillComponentUtilityEffectRepository(path).resolve_component_text(15, 1) == ""
