import json
import sqlite3

from minmax.skill_component_source_stat_rule_repository import (
    SkillComponentSourceStatRuleRepository,
)


def test_repository_resolves_death_knell_from_raw_slot_and_header(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT, raw_description TEXT, raw_json TEXT)"
        )
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER)")
        db.execute(
            "INSERT INTO ability VALUES (?, ?, ?, ?)",
            (
                116197,
                "Increases your Critical Strike Chance against enemies under 33% Health by 10%.",
                "Increases your Critical Strike Chance against enemies under 33% Health by <<1>>.",
                json.dumps({"descHeader": "WITH A GRAVELORD ABILITY SLOTTED"}),
            ),
        )
        db.execute("INSERT INTO skill_rank VALUES (?, ?)", (7390, 116197))

    rows = SkillComponentSourceStatRuleRepository(database).resolve(7390, 1)
    assert len(rows) == 1
    assert rows[0].amount == 0.10
    assert rows[0].target_health_below_fraction == 0.33
