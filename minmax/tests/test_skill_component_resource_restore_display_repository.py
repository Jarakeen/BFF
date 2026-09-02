import sqlite3

from minmax.skill_component_resource_restore_display import (
    SkillComponentRestoreDisplayBasis,
    SkillComponentRestoreDisplayResource,
)
from minmax.skill_component_resource_restore_display_repository import (
    SkillComponentResourceRestoreDisplayRepository,
)


def test_repository_strips_color_tags_and_resolves_constitution(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL)")
        db.execute("CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT)")
        db.execute("INSERT INTO skill_rank VALUES (5636, 29769)")
        db.execute(
            "INSERT INTO ability VALUES (?, ?)",
            (
                29769,
                "You restore |cffffff108|r Magicka and Stamina when you take damage for each piece of Heavy Armor equipped. "
                "This effect can occur once every |cffffff8|r seconds. Current bonus: |cffffff$2|r.",
            ),
        )

    rows = SkillComponentResourceRestoreDisplayRepository(database).resolve(5636, 2)
    assert len(rows) == 1
    assert rows[0].resources == (
        SkillComponentRestoreDisplayResource.MAGICKA,
        SkillComponentRestoreDisplayResource.STAMINA,
    )
    assert rows[0].basis is SkillComponentRestoreDisplayBasis.FLAT_PER_UNIT
    assert rows[0].amount_per_unit == 108.0
