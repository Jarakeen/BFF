from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from services.encounter_boss_guide import EncounterBossGuideError, EncounterBossGuideService
from services.encounter_schema import ensure_encounter_schema


def _database(tmp_path: Path, *, payload: object | None = None) -> Path:
    database = tmp_path / "eso.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE ability(id INTEGER PRIMARY KEY)")
        ensure_encounter_schema(connection)
        connection.execute(
            """
            INSERT INTO content(id, name, slug, content_type)
            VALUES (?, ?, ?, ?)
            """,
            ("rockgrove", "Rockgrove", "rockgrove", "trial"),
        )
        connection.execute(
            """
            INSERT INTO encounter(id, content_id, name, slug)
            VALUES (?, ?, ?, ?)
            """,
            ("xalvakka", "rockgrove", "Xalvakka", "xalvakka"),
        )
        connection.execute(
            "INSERT INTO encounter_health(encounter_id) VALUES (?)",
            ("xalvakka",),
        )
        fact_payload = payload if payload is not None else {
            "thresholds": ["70%", "40%"],
            "event": "retreat",
        }
        cursor = connection.execute(
            """
            INSERT INTO encounter_canonical_fact(
                encounter_id, canonical_kind, fact_type, fact_key,
                payload_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "xalvakka",
                "phase_transition",
                "transition",
                "retreat_thresholds",
                json.dumps(fact_payload),
                "reviewed_corroborated",
            ),
        )
        fact_id = int(cursor.lastrowid)
        for source_name in ("UESP Online:Xalvakka", "Community Rockgrove Guide"):
            connection.execute(
                """
                INSERT INTO encounter_fact_evidence(
                    canonical_fact_id, source_type, source_name, source_value_json
                ) VALUES (?, ?, ?, ?)
                """,
                (fact_id, "guide", source_name, json.dumps(fact_payload)),
            )
        connection.execute(
            """
            INSERT INTO encounter_canonical_fact(
                encounter_id, canonical_kind, fact_type, fact_key,
                payload_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "xalvakka",
                "mechanic_detail",
                "mechanic_detail",
                "ignored_non_timeline_fact",
                json.dumps({"requires_movement": True}),
                "reviewed_corroborated",
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return database


def test_boss_guide_projects_only_reviewed_canonical_timeline_kinds(tmp_path: Path) -> None:
    guide = EncounterBossGuideService(_database(tmp_path)).get("xalvakka")

    assert len(guide.timeline_facts) == 1
    fact = guide.timeline_facts[0]
    assert fact.canonical_kind == "phase_transition"
    assert fact.fact_type == "transition"
    assert fact.fact_key == "retreat_thresholds"
    assert fact.payload == {"thresholds": ["70%", "40%"], "event": "retreat"}
    assert fact.review_status == "reviewed_corroborated"
    assert fact.evidence_count == 2


def test_boss_guide_rejects_malformed_canonical_timeline_payload(tmp_path: Path) -> None:
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE encounter_canonical_fact SET payload_json = ? WHERE canonical_kind = ?",
            ("not-json", "phase_transition"),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(EncounterBossGuideError, match="invalid payload_json"):
        EncounterBossGuideService(database).get("xalvakka")


def test_boss_guide_rejects_non_object_canonical_timeline_payload(tmp_path: Path) -> None:
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE encounter_canonical_fact SET payload_json = ? WHERE canonical_kind = ?",
            (json.dumps(["70%", "40%"]), "phase_transition"),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(EncounterBossGuideError, match="must be a JSON object"):
        EncounterBossGuideService(database).get("xalvakka")
