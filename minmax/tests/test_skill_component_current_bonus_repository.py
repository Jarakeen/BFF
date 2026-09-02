import sqlite3

from minmax.skill_component_current_bonus import SkillComponentCurrentBonusDriver
from minmax.skill_component_current_bonus_repository import SkillComponentCurrentBonusRepository


def _db(path, description):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT)")
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER)")
        db.execute("INSERT INTO ability VALUES (10, ?)", (description,))
        db.execute("INSERT INTO skill_rank VALUES (1, 10)")


def test_repository_strips_color_tags_and_resolves_current_total(tmp_path):
    path = tmp_path / "eso.db"
    _db(
        path,
        "Increases your Weapon and Spell Damage by |cffffff108|r for each Sorcerer ability slotted. "
        "Current bonus: |cffffff$1|r.",
    )
    rows = SkillComponentCurrentBonusRepository(path).resolve(1, 1)
    assert len(rows) == 1
    assert rows[0].driver == SkillComponentCurrentBonusDriver.SORCERER_ABILITIES_SLOTTED
    assert rows[0].amount_per_unit == 108.0


def test_repository_rejects_resource_restore_current_bonus(tmp_path):
    path = tmp_path / "eso.db"
    _db(
        path,
        "Activating a synergy restores 4% of your Max Health, Stamina, and Magicka. "
        "Current Bonus: $1 Health, $2 Stamina, and $3 Magicka.",
    )
    assert SkillComponentCurrentBonusRepository(path).resolve(1, 1) == ()
