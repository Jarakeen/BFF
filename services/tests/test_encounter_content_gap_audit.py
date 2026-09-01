from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.encounter_content_gap_audit import audit_content_encounters
from services.encounter_schema import ensure_encounter_schema


def _packet(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "content_id": "trial_one",
                "encounter_id": "boss_one",
                "encounter_name": "Boss One",
                "evidence": [
                    {
                        "fact_type": "mechanic_state",
                        "fact_key": "storm_exists",
                        "value": True,
                        "source_type": "uesp",
                        "source_name": "UESP",
                    },
                    {
                        "fact_type": "mechanic_state",
                        "fact_key": "storm_exists",
                        "value": True,
                        "source_type": "guide",
                        "source_name": "Guide",
                    },
                    {
                        "fact_type": "phase_state",
                        "fact_key": "execute_exists",
                        "value": True,
                        "source_type": "guide",
                        "source_name": "Guide",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    ensure_encounter_schema(connection)
    connection.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES ('trial_one', 'Trial One', 'trial-one', 'trial')"
    )
    connection.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES ('boss_one', 'trial_one', 'Boss One', 'boss-one')"
    )
    connection.commit()
    return connection


def test_content_gap_audit_reports_missing_eligible_and_review_backlog(tmp_path):
    packet = tmp_path / "boss_one.json"
    _packet(packet)
    connection = _db()
    try:
        audit = audit_content_encounters(
            connection,
            content_id="trial_one",
            packet_dir=tmp_path,
        )
    finally:
        connection.close()

    assert len(audit.database_encounters) == 1
    assert audit.database_encounters[0].npc_count == 0
    assert len(audit.packet_gaps) == 1
    gap = audit.packet_gaps[0]
    assert gap.eligible == ("mechanic_state:storm_exists",)
    assert gap.missing_eligible == ("mechanic_state:storm_exists",)
    assert gap.review_required == ("phase_state:execute_exists",)
    assert gap.blocked == ()


def test_content_gap_audit_recognizes_persisted_eligible_fact(tmp_path):
    packet = tmp_path / "boss_one.json"
    _packet(packet)
    connection = _db()
    try:
        connection.execute(
            """
            INSERT INTO encounter_canonical_fact(
                encounter_id, canonical_kind, fact_type, fact_key, payload_json,
                review_status, valid_from_update, valid_from_patch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "boss_one",
                "mechanic_presence",
                "mechanic_state",
                "storm_exists",
                '{"name":"Storm","present":true}',
                "reviewed_corroborated",
                "",
                "",
            ),
        )
        connection.commit()
        audit = audit_content_encounters(
            connection,
            content_id="trial_one",
            packet_dir=tmp_path,
        )
    finally:
        connection.close()

    gap = audit.packet_gaps[0]
    assert gap.missing_eligible == ()
    assert "mechanic_state:storm_exists" in gap.persisted
    assert audit.encounters_without_packets == ()
    assert audit.packets_without_encounters == ()
