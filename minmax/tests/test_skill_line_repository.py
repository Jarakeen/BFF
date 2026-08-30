import sqlite3

from minmax.skill_line_repository import SkillLineRepository


def test_skill_line_lookup_resolves_unique_active_ability_name(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.execute(
        """
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            class_type TEXT,
            skill_line TEXT,
            is_passive INTEGER
        )
        """
    )
    db.executemany(
        "INSERT INTO ability VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Eternal Guardian", "Warden", "Animal Companions", 0),
            (2, "Frozen Armor", "Warden", "Winter's Embrace", 1),
            (3, "Combat Prayer", "", "Restoration Staff", 0),
        ],
    )
    db.commit()
    db.close()

    repository = SkillLineRepository(path)

    assert repository.skill_line_for_ability_name("Eternal Guardian", class_name="Warden") == "Animal Companions"
    assert repository.skill_line_for_ability_name("Eternal Guardian") == "Animal Companions"
    assert repository.skill_line_for_ability_name("Combat Prayer") == "Restoration Staff"
    assert repository.skill_line_for_ability_name("Combat Prayer", class_name="Warden") is None
    assert repository.skill_line_for_ability_name("Frozen Armor", class_name="Warden") is None
    assert repository.skill_line_for_ability_name("Missing Skill", class_name="Warden") is None
