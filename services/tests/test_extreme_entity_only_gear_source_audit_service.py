from __future__ import annotations

import sqlite3

from services.extreme_entity_only_gear_source_audit_service import (
    ExtremeEntityOnlyGearSourceAuditService,
)


def test_entity_only_gear_source_audit_reports_source_and_raw_payload(tmp_path) -> None:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL
            );
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE entity_source (
                entity_id TEXT NOT NULL,
                source TEXT,
                source_entity_type TEXT,
                source_id TEXT,
                raw_json TEXT
            );

            INSERT INTO entity VALUES ('gear_set:test_arena', 'gear_set', 'Test Arena');
            INSERT INTO entity VALUES ('gear_set:normalized', 'gear_set', 'Normalized');
            INSERT INTO gear_set VALUES (1, 'Normalized');
            INSERT INTO entity_source VALUES (
                'gear_set:test_arena',
                'eso_hub',
                'modifying_sets',
                'abc',
                '{"name":"Test Arena","description":"bonus","items":[1,2]}'
            );
            """
        )

    report = ExtremeEntityOnlyGearSourceAuditService(path).build()

    assert report.entity_count == 1
    assert report.with_source_count == 1
    assert report.with_raw_payload_count == 1
    assert report.without_source_count == 0
    row = report.rows[0]
    assert row.name == "Test Arena"
    assert row.sources == ("eso_hub",)
    assert row.source_entity_types == ("modifying_sets",)
    assert row.raw_json_keys == ("description", "items", "name")
