from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.boss_parent_content_bootstrap import (
    EXISTING,
    MISSING_SOURCE,
    READY,
    audit_boss_parent_content,
)


def _db(*, with_content: bool = False) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute(
        """
        CREATE TABLE content (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            content_type TEXT NOT NULL,
            summary TEXT DEFAULT '',
            location TEXT DEFAULT '',
            group_size INTEGER,
            source_url TEXT DEFAULT '',
            source_title TEXT DEFAULT '',
            revision_id INTEGER,
            retrieved_at TEXT DEFAULT '',
            license TEXT DEFAULT ''
        )
        """
    )
    if with_content:
        db.execute(
            "INSERT INTO content(id, name, content_type) VALUES (?, ?, ?)",
            ("silorn", "Silorn", "dungeon"),
        )
    db.commit()
    return db


def _write_boss(path: Path, content_id: str = "silorn") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"id": "bloodmane", "name": "Bloodmane", "content_id": content_id}),
        encoding="utf-8",
    )


def _write_content(path: Path, content_id: str = "silorn") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": content_id,
                "name": "Silorn",
                "content_type": "dungeon",
                "source": {"revision_id": 123},
            }
        ),
        encoding="utf-8",
    )


def test_missing_parent_is_ready_from_exact_content_source(tmp_path: Path) -> None:
    boss_dir = tmp_path / "bosses"
    content_root = tmp_path / "content"
    _write_boss(boss_dir / "bloodmane.json")
    _write_content(content_root / "dungeons" / "silorn.json")

    audit = audit_boss_parent_content(
        _db(), boss_dir=boss_dir, content_root=content_root
    )

    assert len(audit.candidates) == 1
    row = audit.candidates[0]
    assert row.status == READY
    assert row.content_id == "silorn"
    assert row.content_type == "dungeon"
    assert row.boss_count == 1


def test_existing_parent_is_not_reimport_candidate(tmp_path: Path) -> None:
    boss_dir = tmp_path / "bosses"
    content_root = tmp_path / "content"
    _write_boss(boss_dir / "bloodmane.json")
    _write_content(content_root / "dungeons" / "silorn.json")

    audit = audit_boss_parent_content(
        _db(with_content=True), boss_dir=boss_dir, content_root=content_root
    )

    assert audit.candidates[0].status == EXISTING
    assert len(audit.ready) == 0
    assert len(audit.existing) == 1


def test_missing_exact_content_source_blocks_without_inference(tmp_path: Path) -> None:
    boss_dir = tmp_path / "bosses"
    content_root = tmp_path / "content"
    _write_boss(boss_dir / "bloodmane.json", content_id="unknown_place")
    _write_content(content_root / "dungeons" / "silorn.json")

    audit = audit_boss_parent_content(
        _db(), boss_dir=boss_dir, content_root=content_root
    )

    assert audit.candidates[0].status == MISSING_SOURCE
    assert len(audit.blocked) == 1
