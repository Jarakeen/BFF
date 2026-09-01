from __future__ import annotations

import sqlite3

from services.encounter_schema import ensure_encounter_schema


def _legacy_content_schema(db: sqlite3.Connection) -> None:
    db.executescript(
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
        );
        """
    )
    db.execute(
        """
        INSERT INTO content(
            id, name, content_type, summary, location, group_size,
            source_url, source_title, revision_id, retrieved_at, license
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "dreadsail_reef",
            "Dreadsail Reef",
            "trial",
            "legacy summary",
            "High Isle",
            12,
            "https://en.uesp.net/wiki/Online:Dreadsail_Reef",
            "Online:Dreadsail Reef",
            123456,
            "2026-09-01T00:00:00+00:00",
            "CC BY-SA",
        ),
    )
    db.commit()


def test_encounter_schema_reuses_existing_legacy_content_table() -> None:
    db = sqlite3.connect(":memory:")
    _legacy_content_schema(db)

    before_columns = [row[1] for row in db.execute("PRAGMA table_info(content)")]
    before_row = db.execute(
        "SELECT id, name, content_type, group_size, source_title, revision_id FROM content"
    ).fetchone()

    ensure_encounter_schema(db)

    after_columns = [row[1] for row in db.execute("PRAGMA table_info(content)")]
    after_row = db.execute(
        "SELECT id, name, content_type, group_size, source_title, revision_id FROM content"
    ).fetchone()

    assert after_columns == before_columns
    assert after_row == before_row
    assert {
        "encounter",
        "encounter_canonical_fact",
        "encounter_fact_evidence",
        "encounter_schema_meta",
    }.issubset(
        {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    )


def test_encounter_row_can_reference_legacy_content_parent() -> None:
    db = sqlite3.connect(":memory:")
    _legacy_content_schema(db)
    ensure_encounter_schema(db)

    db.execute(
        """
        INSERT INTO encounter(id, content_id, name, slug)
        VALUES (?, ?, ?, ?)
        """,
        (
            "tideborn_taleria",
            "dreadsail_reef",
            "Tideborn Taleria",
            "tideborn-taleria",
        ),
    )
    db.commit()

    assert db.execute(
        "SELECT content_id, name FROM encounter WHERE id = ?",
        ("tideborn_taleria",),
    ).fetchone() == ("dreadsail_reef", "Tideborn Taleria")
