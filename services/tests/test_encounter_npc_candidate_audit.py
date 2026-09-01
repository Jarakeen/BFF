from __future__ import annotations

import sqlite3

from services.encounter_npc_candidate_audit import (
    audit_encounter_npc_candidates,
    encounter_search_names,
)


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE encounter (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE entity (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        );
        CREATE TABLE entity_source (
            id INTEGER PRIMARY KEY,
            entity_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_entity_type TEXT,
            source_id TEXT,
            source_name TEXT,
            raw_json TEXT
        );
        CREATE TABLE encounter_npc (
            encounter_id TEXT NOT NULL,
            npc_entity_id TEXT NOT NULL,
            PRIMARY KEY (encounter_id, npc_entity_id)
        );
        """
    )
    return connection


def test_multi_actor_encounter_searches_combined_and_individual_names():
    assert encounter_search_names("Lylanar and Turlassil") == (
        "Lylanar and Turlassil",
        "Lylanar",
        "Turlassil",
    )


def test_audit_returns_exact_entity_and_source_candidates_without_mutating_links():
    connection = _db()
    connection.execute(
        "INSERT INTO encounter(id, content_id, name) VALUES ('boss1', 'dsr', 'Lylanar and Turlassil')"
    )
    connection.executemany(
        "INSERT INTO entity(id, entity_type, name, slug) VALUES (?, 'npc', ?, ?)",
        [
            ("npc:lylanar", "Lylanar", "lylanar"),
            ("npc:turlassil", "Turlassil", "turlassil"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO entity_source(entity_id, source, source_entity_type, source_id, source_name)
        VALUES (?, 'UESP', 'npc', ?, ?)
        """,
        [
            ("npc:lylanar", "100", "Lylanar"),
            ("npc:turlassil", "200", "Turlassil"),
        ],
    )

    rows = audit_encounter_npc_candidates(connection, "dsr")

    assert len(rows) == 1
    assert rows[0].existing_npc_ids == ()
    assert {candidate.entity_id for candidate in rows[0].candidates} == {
        "npc:lylanar",
        "npc:turlassil",
    }
    assert connection.execute("SELECT COUNT(*) FROM encounter_npc").fetchone()[0] == 0
