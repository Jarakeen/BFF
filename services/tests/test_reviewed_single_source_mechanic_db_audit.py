from __future__ import annotations

import sqlite3

from services.encounter_persistence_plan import (
    EncounterPersistencePlan,
    PlannedCanonicalFactRow,
    PlannedEvidenceRow,
)
from services.reviewed_single_source_mechanic_db_audit import (
    audit_reviewed_single_source_database,
)


def _plan() -> EncounterPersistencePlan:
    fact = PlannedCanonicalFactRow(
        logical_ref="mechanic_detail:quake",
        encounter_id="gargoyle",
        canonical_kind="mechanic_detail",
        fact_type="mechanic_detail",
        fact_key="quake",
        payload_json='{"name":"Quake"}',
        review_status="reviewed_single_source",
        valid_from_update="",
        valid_from_patch="",
    )
    evidence = PlannedEvidenceRow(
        canonical_fact_ref=fact.logical_ref,
        source_type="uesp_boss_source",
        source_name="UESP",
        source_locator="https://example.invalid/gargoyle",
        source_revision="123",
        game_update="",
        patch_version="",
        confidence="reviewed",
        source_value_json=fact.payload_json,
        notes="source_family=uesp\nreview_status=reviewed_single_source",
    )
    return EncounterPersistencePlan(fact=fact, evidence=(evidence,))


def _connection() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(
        """
        CREATE TABLE encounter_canonical_fact (
            id INTEGER PRIMARY KEY,
            encounter_id TEXT NOT NULL,
            canonical_kind TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            fact_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            review_status TEXT NOT NULL,
            valid_from_update TEXT NOT NULL,
            valid_from_patch TEXT NOT NULL
        );
        CREATE TABLE encounter_fact_evidence (
            id INTEGER PRIMARY KEY,
            canonical_fact_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_locator TEXT NOT NULL,
            source_revision TEXT NOT NULL,
            game_update TEXT NOT NULL,
            patch_version TEXT NOT NULL,
            confidence TEXT NOT NULL,
            source_value_json TEXT NOT NULL,
            notes TEXT NOT NULL
        );
        """
    )
    return con


def _insert_plan(con: sqlite3.Connection, plan: EncounterPersistencePlan) -> None:
    fact = plan.fact
    cur = con.execute(
        """
        INSERT INTO encounter_canonical_fact (
            encounter_id, canonical_kind, fact_type, fact_key, payload_json,
            review_status, valid_from_update, valid_from_patch
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fact.encounter_id,
            fact.canonical_kind,
            fact.fact_type,
            fact.fact_key,
            fact.payload_json,
            fact.review_status,
            fact.valid_from_update,
            fact.valid_from_patch,
        ),
    )
    evidence = plan.evidence[0]
    con.execute(
        """
        INSERT INTO encounter_fact_evidence (
            canonical_fact_id, source_type, source_name, source_locator,
            source_revision, game_update, patch_version, confidence,
            source_value_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(cur.lastrowid),
            evidence.source_type,
            evidence.source_name,
            evidence.source_locator,
            evidence.source_revision,
            evidence.game_update,
            evidence.patch_version,
            evidence.confidence,
            evidence.source_value_json,
            evidence.notes,
        ),
    )


def test_audit_matches_exact_persisted_fact_and_evidence() -> None:
    plan = _plan()
    con = _connection()
    _insert_plan(con, plan)

    audit = audit_reviewed_single_source_database(con, [plan])

    assert not audit.blocked
    assert audit.matched_facts == 1
    assert audit.matched_evidence == 1


def test_audit_reports_missing_fact() -> None:
    audit = audit_reviewed_single_source_database(_connection(), [_plan()])

    assert audit.blocked
    assert audit.matched_facts == 0
    assert len(audit.missing_facts) == 1


def test_audit_reports_conflicting_evidence() -> None:
    plan = _plan()
    con = _connection()
    _insert_plan(con, plan)
    con.execute("UPDATE encounter_fact_evidence SET notes = 'wrong'")

    audit = audit_reviewed_single_source_database(con, [plan])

    assert audit.blocked
    assert audit.matched_facts == 1
    assert audit.matched_evidence == 0
    assert len(audit.conflicting_evidence) == 1
