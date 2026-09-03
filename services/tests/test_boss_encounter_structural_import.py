from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.boss_encounter_structural_import import (
    READY,
    apply_boss_structural_import,
    audit_boss_structural_import,
)
from services.encounter_schema import ensure_encounter_schema


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    ensure_encounter_schema(db)
    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("rockgrove", "Rockgrove", "rockgrove", "trial"),
    )
    db.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
        ("oaxiltso", "rockgrove", "Oaxiltso", "oaxiltso"),
    )
    db.commit()
    return db


def _write(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "oaxiltso",
                "name": "Oaxiltso",
                "content_id": "rockgrove",
                "health": {"normal": "10", "veteran": "20", "hardmode": "30"},
                "abilities": [
                    {"name": "Noxious Sludge", "description": "Poisons two targets."},
                    {"name": "Savage Blitz", "description": "Charges the farthest target."},
                ],
                "mechanics": [
                    {
                        "name": "Noxious Sludge",
                        "description": "Poisons two targets.",
                        "mechanic_type": "targeted_hazard",
                        "interpretation_status": "inferred",
                    }
                ],
                "phases": [
                    {"label": "Burn", "threshold": "50%", "description": "Burn phase."}
                ],
                "dialogue": [
                    {
                        "trigger": "Noxious Sludge attack:",
                        "speaker": "Oaxiltso",
                        "line": "Spit!",
                        "ability": "Noxious Sludge",
                    }
                ],
                "difficulty_notes": {"hardmode_info": ["Harder."], "normal_veteran_differences": []},
                "notes": ["note"],
                "strategy_notes": ["strategy"],
                "related_npcs": [],
                "related_quests": ["quest"],
                "source": {
                    "url": "https://en.uesp.net/wiki/Online:Oaxiltso",
                    "revision_id": 3304340,
                },
            }
        ),
        encoding="utf-8",
    )


def test_audit_accepts_source_backed_structure(tmp_path: Path) -> None:
    db = _db()
    _write(tmp_path / "oaxiltso.json")

    audit = audit_boss_structural_import(db, tmp_path)

    assert len(audit.ready) == 1
    assert audit.ready[0].status == READY
    assert audit.ability_count == 2
    assert audit.phase_count == 1
    assert audit.dialogue_count == 1
    assert audit.blocked == ()


def test_apply_writes_structure_but_not_inferred_mechanics(tmp_path: Path) -> None:
    db = _db()
    _write(tmp_path / "oaxiltso.json")

    audit = audit_boss_structural_import(db, tmp_path)
    assert apply_boss_structural_import(db, audit) == (1, 2, 1, 1)

    assert db.execute(
        "SELECT normal, veteran, hardmode FROM encounter_health WHERE encounter_id='oaxiltso'"
    ).fetchone() == ("10", "20", "30")
    assert db.execute(
        "SELECT name, interruptible FROM encounter_ability WHERE encounter_id='oaxiltso' ORDER BY name"
    ).fetchall() == [("Noxious Sludge", None), ("Savage Blitz", None)]
    assert db.execute("SELECT COUNT(*) FROM encounter_phase").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM encounter_dialogue").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM encounter_mechanic").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM encounter_canonical_fact").fetchone()[0] == 0


def test_apply_is_idempotent(tmp_path: Path) -> None:
    db = _db()
    _write(tmp_path / "oaxiltso.json")

    first = audit_boss_structural_import(db, tmp_path)
    apply_boss_structural_import(db, first)
    second = audit_boss_structural_import(db, tmp_path)
    apply_boss_structural_import(db, second)

    assert db.execute("SELECT COUNT(*) FROM encounter_ability").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM encounter_phase").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM encounter_dialogue").fetchone()[0] == 1
