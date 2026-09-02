import sqlite3

from minmax.skill_component_effect_relationship_repository import (
    SkillComponentEffectRelationshipRepository,
)


def test_repository_uses_effect_table_when_combat_effect_lacks_named_effect(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT)")
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER)")
        db.execute("CREATE TABLE combat_effect (name TEXT)")
        db.execute("CREATE TABLE effect (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute(
            "INSERT INTO ability(ability_id, coef_description) VALUES (?, ?)",
            (183165, "Craft a rune that deals $1 Magic Damage and applies Minor Maim for 15 seconds."),
        )
        db.execute("INSERT INTO skill_rank(id, ability_id) VALUES (?, ?)", (7507, 183165))
        db.execute("INSERT INTO effect(id, name) VALUES (?, ?)", (1, "Minor Maim"))

    rows = SkillComponentEffectRelationshipRepository(database).resolve(7507, 1)
    assert len(rows) == 1
    assert rows[0].target_effect == "minor_maim"
    assert rows[0].source_effect_name == "Minor Maim"
