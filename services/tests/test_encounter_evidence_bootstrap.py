from __future__ import annotations

import json
import sqlite3

from services.encounter_evidence_bootstrap import (
    build_encounter_bootstrap_plan_from_evidence,
)


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE content (id TEXT PRIMARY KEY, name TEXT NOT NULL, content_type TEXT NOT NULL)"
    )
    db.execute(
        "INSERT INTO content(id, name, content_type) VALUES (?, ?, ?)",
        ("dreadsail_reef", "Dreadsail Reef", "trial"),
    )
    return db


def test_builds_internal_bootstrap_plan_from_reviewed_packet(tmp_path):
    packet = tmp_path / "reef_guardian.json"
    packet.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "content_id": "dreadsail_reef",
                "encounter_id": "reef_guardian",
                "encounter_name": "Reef Guardian",
                "evidence": [],
            }
        ),
        encoding="utf-8",
    )

    plan = build_encounter_bootstrap_plan_from_evidence(_db(), packet)

    assert plan.bootstrap_source == "encounter_evidence_packet"
    assert plan.encounter_id == "reef_guardian"
    assert plan.content_id == "dreadsail_reef"
    assert plan.name == "Reef Guardian"
    assert plan.slug == "reef-guardian"
    assert plan.source_revision_id == ""
    assert plan.source_page_title == "Encounter evidence packet: reef_guardian.json"


def test_refuses_packet_with_missing_content_parent(tmp_path):
    packet = tmp_path / "reef_guardian.json"
    packet.write_text(
        json.dumps(
            {
                "content_id": "missing_trial",
                "encounter_id": "reef_guardian",
                "encounter_name": "Reef Guardian",
                "evidence": [],
            }
        ),
        encoding="utf-8",
    )

    try:
        build_encounter_bootstrap_plan_from_evidence(_db(), packet)
    except RuntimeError as exc:
        assert "Content row does not exist" in str(exc)
    else:
        raise AssertionError("missing content parent should be rejected")
