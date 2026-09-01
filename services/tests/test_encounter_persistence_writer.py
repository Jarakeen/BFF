from __future__ import annotations

import sqlite3

import pytest

from services.encounter_persistence_plan import (
    EncounterPersistencePlan,
    PlannedCanonicalFactRow,
    PlannedEvidenceRow,
)
from services.encounter_persistence_writer import (
    persist_encounter_plans,
    validate_persistence_target,
)


def _connection() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(
        """
        CREATE TABLE content (id TEXT PRIMARY KEY, name TEXT NOT NULL, content_type TEXT NOT NULL);
        CREATE TABLE encounter (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL REFERENCES content(id),
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        );
        CREATE TABLE encounter_canonical_fact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id TEXT NOT NULL REFERENCES encounter(id) ON DELETE CASCADE,
            canonical_kind TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            fact_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            review_status TEXT NOT NULL,
            valid_from_update TEXT DEFAULT '',
            valid_to_update TEXT DEFAULT '',
            valid_from_patch TEXT DEFAULT '',
            valid_to_patch TEXT DEFAULT '',
            UNIQUE(encounter_id, fact_type, fact_key, valid_from_update, valid_from_patch)
        );
        CREATE TABLE encounter_fact_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_fact_id INTEGER NOT NULL REFERENCES encounter_canonical_fact(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_locator TEXT DEFAULT '',
            source_revision TEXT DEFAULT '',
            game_update TEXT DEFAULT '',
            patch_version TEXT DEFAULT '',
            confidence TEXT NOT NULL,
            source_value_json TEXT NOT NULL,
            notes TEXT DEFAULT '',
            UNIQUE(canonical_fact_id, source_type, source_name, source_locator, source_revision, game_update, patch_version)
        );
        """
    )
    con.execute("INSERT INTO content(id, name, content_type) VALUES ('dreadsail_reef', 'Dreadsail Reef', 'trial')")
    con.execute("INSERT INTO encounter(id, content_id, name, slug) VALUES ('tideborn_taleria', 'dreadsail_reef', 'Tideborn Taleria', 'tideborn-taleria')")
    return con


def _plan(payload: str = '{"name":"Rapid Deluge","present":true}') -> EncounterPersistencePlan:
    fact = PlannedCanonicalFactRow(
        logical_ref="mechanic_state:rapid_deluge_exists",
        encounter_id="tideborn_taleria",
        canonical_kind="mechanic_presence",
        fact_type="mechanic_state",
        fact_key="rapid_deluge_exists",
        payload_json=payload,
        review_status="reviewed_corroborated",
        valid_from_update="",
        valid_from_patch="",
    )
    evidence = (
        PlannedEvidenceRow(
            canonical_fact_ref=fact.logical_ref,
            source_type="uesp",
            source_name="UESP",
            source_locator="Rapid Deluge",
            source_revision="3582555",
            game_update="",
            patch_version="",
            confidence="high",
            source_value_json="true",
            notes="",
        ),
        PlannedEvidenceRow(
            canonical_fact_ref=fact.logical_ref,
            source_type="combat_addon",
            source_name="Combat Alerts 2.6.2",
            source_locator="modules/u34.lua:deluge",
            source_revision="",
            game_update="",
            patch_version="",
            confidence="high",
            source_value_json="true",
            notes="",
        ),
    )
    return EncounterPersistencePlan(fact=fact, evidence=evidence)


def test_writer_inserts_fact_and_multiple_evidence_rows_idempotently():
    con = _connection()
    first = persist_encounter_plans(con, [_plan()])
    con.commit()

    assert first.facts_inserted == 1
    assert first.evidence_inserted == 2
    assert con.execute("SELECT COUNT(*) FROM encounter_canonical_fact").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM encounter_fact_evidence").fetchone()[0] == 2

    second = persist_encounter_plans(con, [_plan()])
    con.commit()
    assert second.facts_inserted == 0
    assert second.facts_existing == 1
    assert second.evidence_inserted == 0
    assert second.evidence_existing == 2


def test_writer_refuses_missing_canonical_encounter():
    con = _connection()
    con.execute("DELETE FROM encounter")
    with pytest.raises(RuntimeError, match="Canonical encounter row does not exist"):
        validate_persistence_target(con, [_plan()])


def test_writer_refuses_existing_conflicting_payload():
    con = _connection()
    persist_encounter_plans(con, [_plan()])
    con.commit()

    with pytest.raises(RuntimeError, match="conflicts with reviewed plan"):
        persist_encounter_plans(con, [_plan('{"name":"Rapid Deluge","present":false}')])
