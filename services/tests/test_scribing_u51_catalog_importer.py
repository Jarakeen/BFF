from __future__ import annotations

import json
import sqlite3

from importers.scribing_u51_catalog_importer import U51ScribingCatalogImporter


def _payload(path):
    payload = {
        "source": {"game_update": 51, "channel": "PTS", "scripts_record": "craftedScripts51pts", "skills_record": "craftedSkills51pts", "description_record": "craftedScriptDescriptions51pts", "scripts_sha256": "a", "skills_sha256": "b", "description_sha256": "c"},
        "scripts": [
            {"script_id": 20, "slot": 1, "name": "Damage Shield", "description": "Adds a damage shield.", "hint": "", "icon": "focus.dds"},
            {"script_id": 55, "slot": 3, "name": "Courage", "description": "Adds Courage.", "hint": "", "icon": "affix.dds"},
        ],
        "skills": [
            {"crafted_ability_id": 8, "ability_id": 217462, "ability_ids": [217459, 217462], "skill_type": 4, "name": "Soul Burst", "description": "Unleash a powerful burst.", "hint": "", "icon": "grimoire.dds", "focus_script_ids": [20], "signature_script_ids": [], "affix_script_ids": [55]}
        ],
        "descriptions": [
            {"source_row_id": 1, "crafted_ability_id": 8, "script_id": 55, "class_id": 0, "ability_id": 217462, "name": "Warding Burst", "description_raw": "Grants |cffffff215|r Weapon and Spell Damage.", "description": "Grants 215 Weapon and Spell Damage."}
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_u51_catalog_imports_scripts_skills_compatibility_and_clean_descriptions(tmp_path):
    database = tmp_path / "eso.db"
    catalog = tmp_path / "catalog.json"
    _payload(catalog)
    summary = U51ScribingCatalogImporter(database).run(catalog_path=catalog)
    assert (summary.scripts, summary.skills, summary.skill_abilities, summary.compatibility_rows, summary.descriptions) == (2, 1, 2, 2, 1)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT script_type, name FROM scribing_u51_script WHERE script_id = 20").fetchone() == ("focus", "Damage Shield")
        assert connection.execute("SELECT slot, script_id FROM scribing_u51_skill_script WHERE crafted_ability_id = 8 ORDER BY slot, script_id").fetchall() == [(1, 20), (3, 55)]
        assert connection.execute("SELECT description_raw, description FROM scribing_crafted_script_description WHERE crafted_ability_id = 8 AND script_id = 55").fetchone() == ("Grants |cffffff215|r Weapon and Spell Damage.", "Grants 215 Weapon and Spell Damage.")
