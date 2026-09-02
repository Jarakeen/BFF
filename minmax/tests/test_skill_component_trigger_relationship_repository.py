import sqlite3

from minmax.skill_component_trigger_relationship import SkillComponentTriggerType
from minmax.skill_component_trigger_relationship_repository import (
    SkillComponentTriggerRelationshipRepository,
)


def _db(tmp_path, description: str):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT)")
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER)")
        db.execute("INSERT INTO ability VALUES (100, ?)", (description,))
        db.execute("INSERT INTO skill_rank VALUES (10, 100)")
    return path


def test_repository_resolves_color_tagged_trigger(tmp_path):
    path = _db(
        tmp_path,
        "When the shield ends the latent heat warms the target, healing them for |cffffff$2|r Health.",
    )
    rows = SkillComponentTriggerRelationshipRepository(path).resolve(10, 2)
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.EFFECT_ENDED


def test_repository_does_not_guess_bare_conditional(tmp_path):
    path = _db(tmp_path, "When conditions are met, deal $1 Flame Damage.")
    assert SkillComponentTriggerRelationshipRepository(path).resolve(10, 1) == ()
