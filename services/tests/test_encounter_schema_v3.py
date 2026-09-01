from __future__ import annotations

import json
import sqlite3

from services.encounter_schema import SCHEMA_VERSION, ensure_encounter_schema


def test_schema_v3_preserves_existing_encounter_rows() -> None:
    db = sqlite3.connect(":memory:")
    ensure_encounter_schema(db)

    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("dreadsail_reef", "Dreadsail Reef", "dreadsail-reef", "trial"),
    )
    db.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
        ("taleria", "dreadsail_reef", "Tideborn Taleria", "tideborn-taleria"),
    )
    db.commit()

    ensure_encounter_schema(db)

    row = db.execute(
        "SELECT name, slug FROM encounter WHERE id = ?",
        ("taleria",),
    ).fetchone()
    assert row == ("Tideborn Taleria", "tideborn-taleria")
    assert SCHEMA_VERSION == 3
    assert db.execute(
        "SELECT value FROM encounter_schema_meta WHERE key = 'schema_version'"
    ).fetchone() == ("3",)


def test_canonical_fact_can_retain_multiple_independent_sources() -> None:
    db = sqlite3.connect(":memory:")
    ensure_encounter_schema(db)

    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("dreadsail_reef", "Dreadsail Reef", "dreadsail-reef", "trial"),
    )
    db.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
        ("taleria", "dreadsail_reef", "Tideborn Taleria", "tideborn-taleria"),
    )

    payload = {"thresholds": ["50%", "35%", "20%"]}
    cursor = db.execute(
        """
        INSERT INTO encounter_canonical_fact(
            encounter_id, canonical_kind, fact_type, fact_key, payload_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            "taleria",
            "phase_transition",
            "transition",
            "bridge_thresholds",
            json.dumps(payload, sort_keys=True),
        ),
    )
    fact_id = cursor.lastrowid

    for source_type, source_name, revision in (
        ("uesp", "UESP Online:Tideborn Taleria", "3582555"),
        ("guide", "Nilandia's Guide to Veteran Dreadsail Reef", ""),
        ("combat_addon", "Combat Alerts 2.6.2", "u34"),
    ):
        db.execute(
            """
            INSERT INTO encounter_fact_evidence(
                canonical_fact_id,
                source_type,
                source_name,
                source_revision,
                confidence,
                source_value_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                source_type,
                source_name,
                revision,
                "high",
                json.dumps(payload, sort_keys=True),
            ),
        )
    db.commit()

    assert db.execute(
        "SELECT COUNT(*) FROM encounter_fact_evidence WHERE canonical_fact_id = ?",
        (fact_id,),
    ).fetchone() == (3,)


def test_deleting_canonical_fact_cascades_evidence_only() -> None:
    db = sqlite3.connect(":memory:")
    ensure_encounter_schema(db)

    db.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("dreadsail_reef", "Dreadsail Reef", "dreadsail-reef", "trial"),
    )
    db.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
        ("taleria", "dreadsail_reef", "Tideborn Taleria", "tideborn-taleria"),
    )
    cursor = db.execute(
        """
        INSERT INTO encounter_canonical_fact(
            encounter_id, canonical_kind, fact_type, fact_key, payload_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        ("taleria", "mechanic_presence", "mechanic_state", "rapid_deluge_exists", "true"),
    )
    fact_id = cursor.lastrowid
    db.execute(
        """
        INSERT INTO encounter_fact_evidence(
            canonical_fact_id, source_type, source_name, source_value_json
        ) VALUES (?, ?, ?, ?)
        """,
        (fact_id, "uesp", "UESP Online:Tideborn Taleria", "true"),
    )
    db.commit()

    db.execute("DELETE FROM encounter_canonical_fact WHERE id = ?", (fact_id,))
    db.commit()

    assert db.execute("SELECT COUNT(*) FROM encounter_fact_evidence").fetchone() == (0,)
    assert db.execute("SELECT COUNT(*) FROM encounter WHERE id = 'taleria'").fetchone() == (1,)
