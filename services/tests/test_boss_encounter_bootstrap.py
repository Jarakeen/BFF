from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from services.boss_encounter_bootstrap import (
    EXISTING,
    MISSING_CONTENT,
    READY,
    apply_boss_encounter_bootstrap,
    audit_boss_encounter_bootstrap,
)
from services.encounter_schema import ensure_encounter_schema


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    ensure_encounter_schema(db)
    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("halls_of_fabrication", "Halls of Fabrication", "halls-of-fabrication", "trial"),
    )
    db.commit()
    return db


def _pre_encounter_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute(
        """
        CREATE TABLE content (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            content_type TEXT NOT NULL,
            summary TEXT DEFAULT '',
            location TEXT DEFAULT '',
            source_url TEXT,
            source_page_title TEXT,
            source_revision_id TEXT,
            retrieved_at TEXT,
            source_license TEXT
        )
        """
    )
    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("halls_of_fabrication", "Halls of Fabrication", "halls-of-fabrication", "trial"),
    )
    db.commit()
    return db


def _write_boss(path: Path, *, content_id: str = "halls_of_fabrication") -> None:
    path.write_text(
        json.dumps(
            {
                "id": "archcustodian",
                "name": "Archcustodian",
                "content_id": content_id,
                "summary": "Third boss.",
                "location": "Transport Circuit",
                "species": "Dwarven Spider",
                "reaction": "Hostile",
                "source": {
                    "url": "https://en.uesp.net/wiki/Online:Archcustodian",
                    "page_title": "Online:Archcustodian",
                    "revision_id": 3175476,
                    "retrieved_at": "2026-08-12T05:32:34Z",
                    "license": "CC BY-SA 2.5 (UESP)",
                },
            }
        ),
        encoding="utf-8",
    )


def test_audit_marks_source_declared_content_ready(tmp_path: Path) -> None:
    db = _db()
    _write_boss(tmp_path / "archcustodian.json")

    audit = audit_boss_encounter_bootstrap(db, tmp_path)

    assert len(audit.candidates) == 1
    row = audit.candidates[0]
    assert row.status == READY
    assert row.encounter_id == "archcustodian"
    assert row.content_id == "halls_of_fabrication"
    assert row.plan is not None
    assert row.plan.source_revision_id == "3175476"


def test_audit_is_read_only_when_encounter_table_does_not_exist(tmp_path: Path) -> None:
    db = _pre_encounter_db()
    _write_boss(tmp_path / "archcustodian.json")

    audit = audit_boss_encounter_bootstrap(db, tmp_path)

    assert audit.candidates[0].status == READY
    assert db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='encounter'"
    ).fetchone() is None


def test_audit_refuses_to_infer_missing_content(tmp_path: Path) -> None:
    db = _db()
    _write_boss(tmp_path / "archcustodian.json", content_id="not_canonical")

    audit = audit_boss_encounter_bootstrap(db, tmp_path)

    assert audit.candidates[0].status == MISSING_CONTENT
    assert len(audit.blocked) == 1
    with pytest.raises(RuntimeError, match="blocking candidate"):
        apply_boss_encounter_bootstrap(db, audit)
    assert db.execute("SELECT COUNT(*) FROM encounter").fetchone()[0] == 0


def test_apply_is_atomic_and_idempotent(tmp_path: Path) -> None:
    db = _db()
    _write_boss(tmp_path / "archcustodian.json")

    audit = audit_boss_encounter_bootstrap(db, tmp_path)
    assert apply_boss_encounter_bootstrap(db, audit) == (1, 0)

    row = db.execute(
        "SELECT id, content_id, name, source_revision_id FROM encounter"
    ).fetchone()
    assert row == ("archcustodian", "halls_of_fabrication", "Archcustodian", "3175476")

    second = audit_boss_encounter_bootstrap(db, tmp_path)
    assert second.candidates[0].status == EXISTING
    assert apply_boss_encounter_bootstrap(db, second) == (0, 1)
