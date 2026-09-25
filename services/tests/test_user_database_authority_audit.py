from __future__ import annotations

import sqlite3
from pathlib import Path

from tools.audit_user_database_authority import audit_database


def test_database_authority_audit_reads_plans_and_revisions_without_writing(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE raid_plan (plan_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE raid_plan_revision (revision_id INTEGER PRIMARY KEY, plan_id TEXT NOT NULL, payload_json TEXT NOT NULL, saved_at TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json, updated_at) VALUES (?, ?, ?)",
            (
                "sunspire-performance-mode-gs",
                '{"plan_id":"sunspire-performance-mode-gs","name":"Core Team","team_name":"Performance Mode","trial_id":"sunspire","members":[{"seat_id":"tank-1","gamertag":"Rikbacon"}]}',
                "2026-09-25 01:55:17",
            ),
        )
        db.execute(
            "INSERT INTO raid_plan_revision(revision_id, plan_id, payload_json, saved_at) VALUES (1, ?, '{}', ?)",
            ("sunspire-performance-mode-gs", "2026-09-25 01:54:00"),
        )

    before = database.read_bytes()
    result = audit_database(database)
    after = database.read_bytes()

    assert before == after
    assert result.exists is True
    assert result.plan_count == 1
    assert result.revision_count == 1
    assert result.plans[0]["plan_id"] == "sunspire-performance-mode-gs"
    assert result.plans[0]["occupied_seats"] == 1


def test_database_authority_audit_handles_missing_database_without_creating_it(tmp_path: Path) -> None:
    database = tmp_path / "missing.db"

    result = audit_database(database)

    assert result.exists is False
    assert result.plan_count == 0
    assert result.revision_count == 0
    assert not database.exists()
