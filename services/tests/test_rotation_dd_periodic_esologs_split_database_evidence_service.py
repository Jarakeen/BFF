from __future__ import annotations

import sqlite3

from services.rotation_dd_periodic_esologs_split_database_evidence_service import (
    RotationDDPeriodicEsoLogsSplitDatabaseEvidenceService,
)


def test_numeric_aliases_are_read_from_canonical_database(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"

    with sqlite3.connect(canonical) as db:
        db.execute(
            """
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER,
                morph INTEGER
            )
            """
        )
        db.executemany(
            "INSERT INTO skill_rank (id, skill_id, ability_id, morph) VALUES (?, ?, ?, ?)",
            (
                (1, 77, 1001, 2),
                (2, 77, 1002, 2),
                (3, 77, 9999, 1),
            ),
        )

    with sqlite3.connect(logs) as db:
        db.execute("CREATE TABLE marker (value TEXT)")

    service = RotationDDPeriodicEsoLogsSplitDatabaseEvidenceService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )

    aliases = service._numeric_aliases_for_rank(
        skill_id=77,
        morph=2,
        base_ability_id=1000,
    )

    assert aliases == (1000, 1001, 1002)


def test_split_service_keeps_logs_database_as_event_source(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    canonical.touch()
    logs.touch()

    service = RotationDDPeriodicEsoLogsSplitDatabaseEvidenceService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )

    assert service.canonical_database_path == canonical
    assert service.database_path == logs
