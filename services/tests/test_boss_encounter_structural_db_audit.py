from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.boss_encounter_structural_db_audit import audit_boss_structural_database
from services.boss_encounter_structural_import import apply_boss_structural_import, audit_boss_structural_import
from services.encounter_schema import ensure_encounter_schema


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ability (id INTEGER PRIMARY KEY)")
    ensure_encounter_schema(db)
    db.execute("INSERT INTO content(id,name,slug,content_type) VALUES ('rockgrove','Rockgrove','rockgrove','trial')")
    db.execute("INSERT INTO encounter(id,content_id,name,slug) VALUES ('oaxiltso','rockgrove','Oaxiltso','oaxiltso')")
    db.commit()
    return db


def _payload() -> dict:
    return {
        "id": "oaxiltso",
        "name": "Oaxiltso",
        "health": {"normal": "10", "veteran": "20", "hardmode": "30"},
        "abilities": [{"name": "Noxious Sludge", "description": "Poisons two targets."}],
        "phases": [{"label": "Burn", "threshold": "50%", "description": "Burn phase."}],
        "dialogue": [{"trigger": "Attack:", "speaker": "Oaxiltso", "line": "Spit!", "ability": "Noxious Sludge"}],
        "difficulty_notes": {"hardmode_info": ["Harder."]},
        "notes": ["note"],
        "strategy_notes": ["strategy"],
        "related_npcs": [],
        "related_quests": ["quest"],
        "source": {"url": "https://en.uesp.net/wiki/Online:Oaxiltso", "revision_id": 3304340},
    }


def _write(tmp_path: Path) -> None:
    (tmp_path / "oaxiltso.json").write_text(json.dumps(_payload()), encoding="utf-8")


def test_structural_db_audit_matches_applied_source(tmp_path: Path) -> None:
    db = _db()
    _write(tmp_path)
    apply_boss_structural_import(db, audit_boss_structural_import(db, tmp_path))

    audit = audit_boss_structural_database(db, tmp_path)

    assert audit.blocked is False
    assert audit.bosses == 1
    assert (audit.expected_health, audit.matched_health) == (1, 1)
    assert (audit.expected_abilities, audit.matched_abilities) == (1, 1)
    assert (audit.expected_phases, audit.matched_phases) == (1, 1)
    assert (audit.expected_dialogue, audit.matched_dialogue) == (1, 1)
    assert (audit.expected_sections, audit.matched_sections) == (5, 5)


def test_structural_db_audit_detects_stale_rows(tmp_path: Path) -> None:
    db = _db()
    _write(tmp_path)
    apply_boss_structural_import(db, audit_boss_structural_import(db, tmp_path))
    db.execute("UPDATE encounter_ability SET description='stale' WHERE encounter_id='oaxiltso'")
    db.commit()

    audit = audit_boss_structural_database(db, tmp_path)

    assert audit.blocked is True
    assert audit.matched_abilities == 0
    assert any("ability" in problem for problem in audit.problems)
