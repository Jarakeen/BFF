from __future__ import annotations

import json
import sqlite3

from services.encounter_bootstrap import (
    apply_encounter_bootstrap,
    build_encounter_bootstrap_plan,
)


def _db(*, include_legacy_boss: bool = True) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
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
        CREATE TABLE bosses (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            content_id TEXT,
            content_name TEXT DEFAULT '',
            location TEXT DEFAULT '',
            species TEXT DEFAULT '',
            reaction TEXT DEFAULT '',
            health_normal TEXT DEFAULT '',
            health_veteran TEXT DEFAULT '',
            health_hardmode TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source_title TEXT DEFAULT '',
            revision_id INTEGER,
            retrieved_at TEXT DEFAULT '',
            license TEXT DEFAULT ''
        );
        """
    )
    db.execute(
        "INSERT INTO content(id, name, content_type) VALUES (?, ?, ?)",
        ("dreadsail_reef", "Dreadsail Reef", "trial"),
    )
    if include_legacy_boss:
        db.execute(
            """
            INSERT INTO bosses(
                id, name, content_id, summary, location, species, reaction,
                source_url, source_title, revision_id, retrieved_at, license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy_taleria_384409",
                "Tideborn Taleria",
                "dreadsail_reef",
                "summary",
                "Dreadsail Reef",
                "Maormer",
                "Hostile",
                "https://en.uesp.net/wiki/Online:Tideborn_Taleria",
                "Online:Tideborn Taleria",
                3582555,
                "2026-09-01T00:00:00+00:00",
                "CC BY-SA",
            ),
        )
    db.commit()
    return db


def test_build_bootstrap_plan_resolves_normalized_selector_and_maps_legacy_fields() -> None:
    db = _db()
    plan = build_encounter_bootstrap_plan(db, "tideborn_taleria")

    assert plan.encounter_id == "tideborn_taleria"
    assert plan.legacy_boss_id == "legacy_taleria_384409"
    assert plan.bootstrap_source == "legacy_db"
    assert plan.content_id == "dreadsail_reef"
    assert plan.slug == "tideborn-taleria"
    assert plan.source_revision_id == "3582555"


def test_build_bootstrap_plan_accepts_exact_name() -> None:
    db = _db()
    plan = build_encounter_bootstrap_plan(db, "Tideborn Taleria")

    assert plan.encounter_id == "tideborn_taleria"
    assert plan.legacy_boss_id == "legacy_taleria_384409"


def test_build_bootstrap_plan_falls_back_to_raw_uesp_json(tmp_path) -> None:
    db = _db(include_legacy_boss=False)
    bosses_dir = tmp_path / "bosses"
    bosses_dir.mkdir()
    path = bosses_dir / "tideborn_taleria.json"
    path.write_text(
        json.dumps(
            {
                "id": "tideborn_taleria",
                "name": "Tideborn Taleria",
                "summary": "Recovered boss record",
                "location": "Dreadsail Reef",
                "species": "Maormer",
                "reaction": "Hostile",
                "source": {
                    "url": "https://en.uesp.net/wiki/Online:Tideborn_Taleria",
                    "page_title": "Online:Tideborn Taleria",
                    "revision_id": 3582555,
                    "retrieved_at": "2026-09-01T00:00:00+00:00",
                    "license": "CC BY-SA",
                },
            }
        ),
        encoding="utf-8",
    )

    plan = build_encounter_bootstrap_plan(
        db,
        "tideborn_taleria",
        raw_bosses_dir=bosses_dir,
        content_id="dreadsail_reef",
    )

    assert plan.encounter_id == "tideborn_taleria"
    assert plan.legacy_boss_id == ""
    assert plan.bootstrap_source == "raw_uesp_json"
    assert plan.source_record == str(path)
    assert plan.content_id == "dreadsail_reef"
    assert plan.source_revision_id == "3582555"


def test_apply_bootstrap_initializes_schema_and_inserts_encounter() -> None:
    db = _db()
    plan = build_encounter_bootstrap_plan(db, "tideborn_taleria")

    assert apply_encounter_bootstrap(db, plan) == "inserted"
    db.commit()

    assert db.execute(
        "SELECT content_id, name, slug FROM encounter WHERE id = ?",
        ("tideborn_taleria",),
    ).fetchone() == ("dreadsail_reef", "Tideborn Taleria", "tideborn-taleria")


def test_apply_bootstrap_is_idempotent() -> None:
    db = _db()
    plan = build_encounter_bootstrap_plan(db, "tideborn_taleria")

    assert apply_encounter_bootstrap(db, plan) == "inserted"
    db.commit()
    assert apply_encounter_bootstrap(db, plan) == "existing"
